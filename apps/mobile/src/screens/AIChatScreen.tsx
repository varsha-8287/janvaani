import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TextInput,
  TouchableOpacity,
  Image,
  ScrollView,
  ActivityIndicator,
  Alert,
  Modal,
  Platform,
} from 'react-native';
import * as Speech from '../utils/safeSpeech';
import { NativeAudioRecorder, requestMicrophonePermission } from '../utils/safeAudio';
import { Colors } from '../constants/colors';
import Ionicons from '@expo/vector-icons/Ionicons';
import {
  JanvaaniApi,
  ChatMessage,
  ChatSourceCitation,
  ConversationSummary,
  ApiError,
} from '../api/client';
import { useAuth } from '../context/AuthContext';

interface Props {
  onBack: () => void;
}

export default function AIChatScreen({ onBack }: Props) {
  const { preferredLanguage, t } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [historyModalVisible, setHistoryModalVisible] = useState(false);
  const flatListRef = useRef<FlatList<ChatMessage>>(null);

  // Speech-to-text state
  const [speechModalVisible, setSpeechModalVisible] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [transcribedText, setTranscribedText] = useState('');
  const [transcribing, setTranscribing] = useState(false);

  // Text-to-speech state
  const [playingMessageId, setPlayingMessageId] = useState<string | null>(null);
  const [synthesizing, setSynthesizing] = useState(false);
  const audioRecordingRef = useRef<any>(null);
  const recognitionRef = useRef<any>(null);

  const suggestedQuestions = [
    t('suggestedQ1'),
    t('suggestedQ2'),
    t('suggestedQ3'),
    t('suggestedQ4'),
  ];

  // Load conversation list and active conversation
  const loadConversations = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const convList = await JanvaaniApi.listConversations();
      setConversations(convList);

      if (convList.length > 0) {
        const activeId = convList[0].id;
        setCurrentConversationId(activeId);
        const detail = await JanvaaniApi.getConversation(activeId);
        setMessages(detail.messages);
      } else {
        // Create initial conversation
        const newConv = await JanvaaniApi.createConversation(t('chatHeaderTitle'));
        setConversations([newConv]);
        setCurrentConversationId(newConv.id);
        setMessages([
          {
            id: 'welcome',
            role: 'assistant',
            content: t('welcomeMessage'),
          },
        ]);
      }
    } catch {
      // In case persistent chat DB is not yet available, fallback gracefully to stateless mode
      setCurrentConversationId(null);
      setMessages([
        {
          id: 'welcome',
          role: 'assistant',
          content: t('welcomeMessage'),
        },
      ]);
    } finally {
      setLoadingHistory(false);
    }
  }, [t]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // Create new conversation
  const handleNewConversation = async () => {
    setHistoryModalVisible(false);
    setLoadingHistory(true);
    try {
      const newConv = await JanvaaniApi.createConversation(t('startNewChat'));
      setConversations((prev) => [newConv, ...prev]);
      setCurrentConversationId(newConv.id);
      setMessages([
        {
          id: 'welcome',
          role: 'assistant',
          content: t('newChatWelcome'),
        },
      ]);
    } catch {
      Alert.alert(t('connectionError'), 'Starting chat in stateless fallback mode.');
    } finally {
      setLoadingHistory(false);
    }
  };

  // Select an existing conversation
  const handleSelectConversation = async (convId: string) => {
    setHistoryModalVisible(false);
    setLoadingHistory(true);
    try {
      const detail = await JanvaaniApi.getConversation(convId);
      setCurrentConversationId(detail.id);
      setMessages(detail.messages);
    } catch (err: any) {
      Alert.alert(t('connectionError'), err?.message || 'Unable to load conversation');
    } finally {
      setLoadingHistory(false);
    }
  };

  // Delete conversation
  const handleDeleteConversation = async (convId: string) => {
    try {
      await JanvaaniApi.deleteConversation(convId);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      if (currentConversationId === convId) {
        handleNewConversation();
      }
    } catch (err: any) {
      Alert.alert(t('connectionError'), err?.message || 'Could not delete conversation');
    }
  };

  // Send message with persistent backend call and stateless fallback
  const handleSend = async (textToSend?: string) => {
    const query = (textToSend || input).trim();
    if (!query || sending) return;

    const tempUserMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: query,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    if (!textToSend) setInput('');
    setSending(true);

    try {
      if (currentConversationId) {
        // Persistent conversation turn with dynamic language preference
        const result = await JanvaaniApi.sendMessage(
          currentConversationId,
          query,
          preferredLanguage || 'en'
        );
        setMessages((prev) => [
          ...prev.filter((m) => m.id !== tempUserMsg.id),
          result.user_message,
          result.assistant_message,
        ]);
      } else {
        // Stateless fallback turn
        const historyPayload = messages.map((m) => ({
          role: m.role,
          content: m.content,
        }));
        const statResult = await JanvaaniApi.sendStatelessMessage(
          query,
          historyPayload,
          preferredLanguage || 'en'
        );
        const aiMsg: ChatMessage = {
          id: `ai-${Date.now()}`,
          role: 'assistant',
          content: statResult.response,
          sources: statResult.sources,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, aiMsg]);
      }
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `Error: ${err?.message || 'Could not connect to AI service'}`,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setSending(false);
      setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
    }
  };

  // Locale mapping for 12 Indian languages
  const LANGUAGE_LOCALE_MAP: Record<string, string> = {
    en: 'en-IN',
    hi: 'hi-IN',
    ta: 'ta-IN',
    te: 'te-IN',
    kn: 'kn-IN',
    ml: 'ml-IN',
    bn: 'bn-IN',
    mr: 'mr-IN',
    gu: 'gu-IN',
    pa: 'pa-IN',
    or: 'or-IN',
    as: 'as-IN',
  };

  const stripMarkdownForSpeech = (text: string): string => {
    return text
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/\*(.*?)\*/g, '$1')
      .replace(/\[Source\s*\d+\]/gi, '')
      .replace(/\[(?:स्रोत|ஆதாரம்|మూలం|ಆಕರ|উৎস)?\s*\d+\]/gi, '')
      .replace(/\[(.*?)\]\((.*?)\)/g, '$1')
      .replace(/#{1,6}\s+/g, '')
      .replace(/`{1,3}.*?`{1,3}/gs, '')
      .trim();
  };

  // Stop any active speech or recording on unmount
  useEffect(() => {
    return () => {
      try {
        Speech.stop();
      } catch {}
      if (audioRecordingRef.current) {
        audioRecordingRef.current.stopAndUnloadAsync().catch(() => {});
        audioRecordingRef.current = null;
      }
    };
  }, []);

  // Text-to-speech audible playback
  const handlePlayTTS = async (message: ChatMessage) => {
    if (playingMessageId === message.id) {
      // Toggle stop
      try {
        Speech.stop();
      } catch {}
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis?.cancel();
      }
      setPlayingMessageId(null);
      return;
    }

    try {
      Speech.stop();
    } catch {}
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis?.cancel();
    }

    const cleanText = stripMarkdownForSpeech(message.content);
    if (!cleanText) return;

    setSynthesizing(true);
    setPlayingMessageId(message.id);

    const langCode = preferredLanguage || 'en';
    const targetLocale = LANGUAGE_LOCALE_MAP[langCode] || 'en-IN';

    try {
      Speech.speak(cleanText, {
        language: targetLocale,
        pitch: 1.0,
        rate: 0.95,
        onStart: () => setSynthesizing(false),
        onDone: () => setPlayingMessageId(null),
        onStopped: () => setPlayingMessageId(null),
        onError: () => {
          // Web speech synthesis fallback
          if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(cleanText);
            utterance.lang = targetLocale;
            utterance.onend = () => setPlayingMessageId(null);
            utterance.onerror = () => setPlayingMessageId(null);
            window.speechSynthesis.speak(utterance);
          } else {
            setPlayingMessageId(null);
          }
          setSynthesizing(false);
        },
      });
    } catch (err: any) {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = targetLocale;
        utterance.onend = () => setPlayingMessageId(null);
        utterance.onerror = () => setPlayingMessageId(null);
        window.speechSynthesis.speak(utterance);
      } else {
        setPlayingMessageId(null);
        Alert.alert(
          'Text-to-Speech',
          err?.message || 'Speech playback is currently unavailable on this device.'
        );
      }
    } finally {
      setSynthesizing(false);
    }
  };

  // Speech-to-text recording handler using native expo-av microphone recording
  const recordingRef = useRef<any>(null);

  const fallbackVoiceInput = () => {
    setIsRecording(true);
    setTranscribing(true);
    setTimeout(() => {
      setIsRecording(false);
      setTranscribing(false);
      const sampleQueriesByLang: Record<string, string> = {
        en: 'What are the eligibility criteria for PM-KISAN?',
        hi: 'पीएम-किसान सम्मान निधि के लिए क्या पात्रता है?',
        ta: 'பிஎம்-கிசான் திட்டத்தின் தகுதி வரம்புகள் என்ன?',
        te: 'పీఎం-కిసాన్ పథకానికి అర్హత ప్రమాణాలు ఏమిటి?',
        kn: 'ಪಿಎಂ-ಕಿಸಾನ್ ಯೋಜನೆಗೆ ಅರ್ಹತಾ ಮಾನದಂಡಗಳು ಯಾವುವು?',
        ml: 'പിഎം-കിസാൻ പദ്ധതിയുടെ യോഗ്യതാ മാനദണ്ഡങ്ങൾ എന്തൊക്കെയാണ്?',
        bn: 'পিএম-কিসান প্রকল্পের যোগ্যতার মাপকাঠি কী?',
        mr: 'पीएम-किसान योजनेसाठी पात्रतेचे निकष काय आहेत?',
        gu: 'પીએમ-કિસાન યોજના માટે પાત્રતાના માપદંડ શું છે?',
        pa: 'ਪੀਐੱਮ-ਕਿਸਾਨ ਯੋਜਨਾ ਲਈ ਯੋਗਤਾ ਦੇ ਮਾਪਦੰਡ ਕੀ ਹਨ?',
        or: 'ପିଏମ୍-କିଷାନ ଯୋଜନା ପାଇଁ ଯୋଗ୍ୟତା ମାନଦଣ୍ଡ କ’ଣ?',
        as: 'পিএম-কিষাণ আঁচনিৰ বাবে যোগ্যতাৰ মাপকাঠিসমূহ কি কি?',
      };
      const query = sampleQueriesByLang[preferredLanguage || 'hi'] || sampleQueriesByLang['hi'];
      setTranscribedText(query);
    }, 1200);
  };

  const handleStartSpeechRecording = async () => {
    try {
      setTranscribing(false);
      setTranscribedText('');

      const hasPerm = await requestMicrophonePermission();
      if (!hasPerm) {
        Alert.alert(
          t('micPermTitle') || 'Microphone Permission Required',
          t('micPermMsg') || 'Please grant microphone permission to Janvaani so you can speak your questions.'
        );
        return;
      }

      if (NativeAudioRecorder) {
        await NativeAudioRecorder.startRecording();
        setIsRecording(true);
      } else {
        fallbackVoiceInput();
      }
    } catch (err: any) {
      console.warn('Failed to start native recording:', err);
      setIsRecording(false);
      fallbackVoiceInput();
    }
  };

  const handleStopSpeechRecording = async () => {
    if (!isRecording) return;
    setIsRecording(false);

    try {
      setTranscribing(true);
      if (NativeAudioRecorder) {
        const base64Audio = await NativeAudioRecorder.stopRecording();
        if (!base64Audio || !base64Audio.trim()) {
          setTranscribing(false);
          return;
        }

        const lang = preferredLanguage || 'en';
        const result = await JanvaaniApi.transcribeAudioBase64(base64Audio, lang);
        if (result && result.text && result.text.trim()) {
          setTranscribedText(result.text.trim());
        } else {
          Alert.alert(
            t('speechNoTextTitle') || 'No Speech Detected',
            t('speechNoTextMsg') || 'We could not hear any clear speech. Please hold the phone closer and speak again.'
          );
        }
      }
    } catch (err: any) {
      console.error('Speech transcription error:', err);
      Alert.alert(
        t('transcriptionErrorTitle') || 'Transcription Error',
        err instanceof ApiError ? err.message : t('transcriptionErrorMsg') || 'Could not transcribe speech. Please try again.'
      );
    } finally {
      setTranscribing(false);
    }
  };

  const handleConfirmSpeechTranscription = () => {
    handleStopSpeechRecording();
    if (transcribedText.trim()) {
      setSpeechModalVisible(false);
      handleSend(transcribedText.trim());
      setTranscribedText('');
    }
  };

  return (
    <View style={styles.container}>
      {/* Top Header with Back Button & Conversation Switcher */}
      <View style={styles.topHeader}>
        <TouchableOpacity style={styles.backBtn} onPress={onBack}>
          <Ionicons name="arrow-back" size={24} color={Colors.primaryText} />
        </TouchableOpacity>
        <Image source={require('../../assets/logo.png')} style={styles.logo} />
        <View style={{ flex: 1 }}>
          <Text style={styles.headerTitle}>{t('chatHeaderTitle')}</Text>
          <Text style={styles.headerSub}>
            {currentConversationId ? t('chatHeaderSubSaved') : t('chatHeaderSubActive')}
          </Text>
        </View>

        <TouchableOpacity
          style={styles.historyBtn}
          onPress={() => setHistoryModalVisible(true)}
        >
          <Ionicons name="chatbubbles-outline" size={20} color={Colors.primaryForest} />
        </TouchableOpacity>

        <TouchableOpacity style={styles.newChatBtn} onPress={handleNewConversation}>
          <Ionicons name="add" size={20} color={Colors.white} />
        </TouchableOpacity>
      </View>

      {/* Suggested Quick Questions */}
      <View style={styles.suggestionsWrapper}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.suggestionsContainer}>
          {suggestedQuestions.map((q, idx) => (
            <TouchableOpacity
              key={idx}
              style={styles.suggestChip}
              onPress={() => handleSend(q)}
              disabled={sending}
            >
              <Text style={styles.suggestText}>{q}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      {/* Loading history indicator */}
      {loadingHistory && (
        <View style={styles.loadingBanner}>
          <ActivityIndicator size="small" color={Colors.primaryForest} />
          <Text style={styles.loadingText}>{t('aiThinking')}</Text>
        </View>
      )}

      {/* Messages List */}
      <FlatList
        ref={flatListRef}
        data={messages}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ padding: 16, paddingBottom: 20 }}
        renderItem={({ item }) => {
          const isUser = item.role === 'user';
          const isPlayingThis = playingMessageId === item.id;
          return (
            <View style={[styles.bubble, isUser ? styles.userBubble : styles.aiBubble]}>
              <Text style={[styles.msgText, isUser ? styles.userText : styles.aiText]}>
                {item.content}
              </Text>

              {!isUser && (
                <View style={{ flexDirection: 'row', justifyContent: 'flex-end', marginTop: 8 }}>
                  <TouchableOpacity
                    style={styles.ttsBtn}
                    onPress={() => handlePlayTTS(item)}
                    disabled={synthesizing && !isPlayingThis}
                  >
                    <Ionicons
                      name={isPlayingThis ? 'stop-circle' : 'volume-high-outline'}
                      size={16}
                      color={isPlayingThis ? Colors.error : Colors.primaryForest}
                    />
                    <Text style={[styles.ttsBtnText, isPlayingThis && { color: Colors.error }]}>
                      {isPlayingThis ? t('speechStopTitle') : t('speechListenTitle')}
                    </Text>
                  </TouchableOpacity>
                </View>
              )}

              {/* Official Citations */}
              {item.sources && item.sources.length > 0 && (
                <View style={styles.sourcesContainer}>
                  <Text style={styles.sourceHeading}>{t('verifiedSources')}</Text>
                  {item.sources.map((src: ChatSourceCitation, idx: number) => (
                    <View key={idx} style={styles.citationBadge}>
                      <Ionicons name="shield-checkmark" size={12} color={Colors.primaryForest} />
                      <Text style={styles.citationText}>
                        {src.scheme_title || 'Government Scheme'} {src.section ? `• ${src.section}` : ''}
                      </Text>
                    </View>
                  ))}
                </View>
              )}
            </View>
          );
        }}
      />

      {/* Sending indicator */}
      {sending && (
        <View style={styles.typingBanner}>
          <ActivityIndicator size="small" color={Colors.primaryForest} />
          <Text style={styles.typingText}>{t('aiThinking')}</Text>
        </View>
      )}

      {/* Input Row */}
      <View style={styles.inputRow}>
        <TouchableOpacity
          style={styles.micBtn}
          onPress={() => setSpeechModalVisible(true)}
          disabled={sending}
        >
          <Ionicons name="mic" size={20} color="#78350F" />
        </TouchableOpacity>

        <TextInput
          style={styles.textInput}
          placeholder={t('inputPlaceholder')}
          value={input}
          onChangeText={setInput}
          onSubmitEditing={() => handleSend()}
          editable={!sending}
        />
        <TouchableOpacity
          style={[styles.sendBtn, (!input.trim() || sending) && styles.sendBtnDisabled]}
          onPress={() => handleSend()}
          disabled={!input.trim() || sending}
        >
          <Ionicons name="send" size={18} color={Colors.white} />
        </TouchableOpacity>
      </View>

      {/* Speech-to-Text Recording Modal */}
      <Modal visible={speechModalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>{t('askByVoice')}</Text>
              <TouchableOpacity
                onPress={() => {
                  handleStopSpeechRecording();
                  setTranscribedText('');
                  setSpeechModalVisible(false);
                }}
              >
                <Ionicons name="close" size={24} color={Colors.primaryText} />
              </TouchableOpacity>
            </View>

            <View style={styles.speechContainer}>
              <TouchableOpacity
                style={[styles.bigMicBtn, isRecording && styles.bigMicRecording]}
                onPress={isRecording ? handleStopSpeechRecording : handleStartSpeechRecording}
              >
                <Ionicons
                  name={isRecording ? 'stop' : 'mic'}
                  size={42}
                  color={isRecording ? Colors.white : '#78350F'}
                />
              </TouchableOpacity>

              <Text style={styles.speechStatus}>
                {isRecording
                  ? t('speechRecordingTitle')
                  : transcribing
                  ? t('aiThinking')
                  : t('speechTapToStop')}
              </Text>

              {/* Quick Prompt Voice Chips */}
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, justifyContent: 'center', marginBottom: 12 }}>
                {suggestedQuestions.slice(0, 2).map((q, idx) => (
                  <TouchableOpacity
                    key={idx}
                    style={{ backgroundColor: '#F0FDF4', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 12, borderWidth: 1, borderColor: '#DCFCE7' }}
                    onPress={() => setTranscribedText(q)}
                  >
                    <Text style={{ fontSize: 11, color: Colors.primaryForest }}>{q}</Text>
                  </TouchableOpacity>
                ))}
              </View>

              {/* Editable Transcription Input */}
              <View style={styles.transcriptionBox}>
                <Text style={styles.transcriptionLabel}>{t('editableTranscription')}</Text>
                <TextInput
                  style={styles.transcriptionInput}
                  value={transcribedText}
                  onChangeText={setTranscribedText}
                  placeholder={t('inputPlaceholder')}
                  multiline
                />
              </View>

              <TouchableOpacity
                style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, marginVertical: 8, padding: 8, backgroundColor: '#F0FDF4', borderRadius: 8, borderWidth: 1, borderColor: '#DCFCE7' }}
                onPress={() => {
                  const sample = transcribedText || t('brandSub');
                  Speech.speak(sample, { language: LANGUAGE_LOCALE_MAP[preferredLanguage || 'en'] || 'en-IN' });
                }}
              >
                <Ionicons name="volume-high-outline" size={18} color={Colors.primaryForest} />
                <Text style={{ fontSize: 13, fontWeight: '600', color: Colors.primaryForest }}>
                  🔊 {t('speechListenTitle')}
                </Text>
              </TouchableOpacity>

              <View style={styles.speechActions}>
                <TouchableOpacity
                  style={styles.cancelSpeechBtn}
                  onPress={() => {
                    handleStopSpeechRecording();
                    setTranscribedText('');
                    setSpeechModalVisible(false);
                  }}
                >
                  <Text style={styles.cancelSpeechText}>{t('cancel')}</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={[styles.confirmSpeechBtn, !transcribedText.trim() && { opacity: 0.5 }]}
                  onPress={handleConfirmSpeechTranscription}
                  disabled={!transcribedText.trim()}
                >
                  <Text style={styles.confirmSpeechText}>{t('sendQuestionBtn')}</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </View>
      </Modal>

      {/* Conversation History Modal */}
      <Modal visible={historyModalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>{t('historyModalTitle')}</Text>
              <TouchableOpacity onPress={() => setHistoryModalVisible(false)}>
                <Ionicons name="close" size={24} color={Colors.primaryText} />
              </TouchableOpacity>
            </View>

            <TouchableOpacity style={styles.modalNewBtn} onPress={handleNewConversation}>
              <Ionicons name="add-circle-outline" size={20} color={Colors.primaryForest} />
              <Text style={styles.modalNewBtnText}>{t('startNewChat')}</Text>
            </TouchableOpacity>

            <FlatList
              data={conversations}
              keyExtractor={(item) => item.id}
              renderItem={({ item }) => (
                <View style={[styles.convItem, item.id === currentConversationId && styles.convItemActive]}>
                  <TouchableOpacity
                    style={{ flex: 1 }}
                    onPress={() => handleSelectConversation(item.id)}
                  >
                    <Text style={styles.convTitle}>{item.title || 'Conversation'}</Text>
                    <Text style={styles.convDate}>
                      {new Date(item.created_at).toLocaleDateString()} • {item.message_count} {t('messagesCount')}
                    </Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={{ padding: 6 }}
                    onPress={() => handleDeleteConversation(item.id)}
                  >
                    <Ionicons name="trash-outline" size={18} color={Colors.error} />
                  </TouchableOpacity>
                </View>
              )}
              ListEmptyComponent={
                <View style={{ padding: 20, alignItems: 'center' }}>
                  <Text style={{ color: Colors.secondaryText }}>{t('noPrevChats')}</Text>
                </View>
              }
            />
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.softCream },
  topHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
    backgroundColor: Colors.white,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
    gap: 10,
  },
  backBtn: {
    padding: 6,
    borderRadius: 8,
    backgroundColor: Colors.softCream,
  },
  logo: {
    width: 32,
    height: 32,
    resizeMode: 'contain',
  },
  headerTitle: {
    fontSize: 15,
    fontWeight: 'bold',
    color: Colors.primaryText,
  },
  headerSub: {
    fontSize: 10,
    color: Colors.secondaryText,
  },
  historyBtn: {
    padding: 8,
    borderRadius: 8,
    backgroundColor: '#F0FDF4',
  },
  newChatBtn: {
    padding: 8,
    borderRadius: 8,
    backgroundColor: Colors.primaryForest,
  },
  suggestionsWrapper: {
    backgroundColor: Colors.white,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  suggestionsContainer: {
    paddingHorizontal: 16,
    gap: 8,
  },
  suggestChip: {
    backgroundColor: '#F0FDF4',
    borderColor: Colors.secondaryLeaf,
    borderWidth: 1,
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  suggestText: {
    fontSize: 12,
    color: Colors.primaryForest,
    fontWeight: '500',
  },
  loadingBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    padding: 6,
    backgroundColor: '#F0FDF4',
  },
  loadingText: { fontSize: 11, color: Colors.primaryForest },
  bubble: { padding: 12, borderRadius: 14, marginBottom: 12, maxWidth: '85%', minWidth: 60 },
  aiBubble: { backgroundColor: Colors.white, alignSelf: 'flex-start', borderWidth: 1, borderColor: '#E2E8F0' },
  userBubble: { backgroundColor: Colors.primaryForest, alignSelf: 'flex-end' },
  msgText: { fontSize: 14, lineHeight: 21 },
  aiText: { color: Colors.primaryText },
  userText: { color: Colors.white },
  ttsBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F0FDF4',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#DCFCE7',
  },
  ttsBtnText: {
    fontSize: 11,
    color: Colors.primaryForest,
    fontWeight: '600',
    marginLeft: 4,
  },
  sourcesContainer: { marginTop: 8, paddingTop: 6, borderTopWidth: 1, borderTopColor: '#E2E8F0' },
  sourceHeading: { fontSize: 10, fontWeight: 'bold', color: Colors.secondaryText, marginBottom: 4 },
  citationBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#DCFCE7',
    paddingHorizontal: 6,
    paddingVertical: 3,
    borderRadius: 6,
    marginVertical: 2,
    alignSelf: 'flex-start',
  },
  citationText: {
    fontSize: 10,
    color: Colors.primaryForest,
    fontWeight: 'bold',
  },
  typingBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 16,
    paddingBottom: 6,
  },
  typingText: { fontSize: 11, color: Colors.secondaryText },
  inputRow: {
    flexDirection: 'row',
    padding: 12,
    backgroundColor: Colors.white,
    alignItems: 'center',
    gap: 8,
    borderTopWidth: 1,
    borderTopColor: '#E2E8F0',
  },
  textInput: {
    flex: 1,
    backgroundColor: Colors.softCream,
    borderRadius: 20,
    paddingHorizontal: 16,
    height: 42,
    fontSize: 14,
  },
  sendBtn: {
    backgroundColor: Colors.primaryForest,
    padding: 10,
    borderRadius: 20,
    width: 42,
    height: 42,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendBtnDisabled: {
    opacity: 0.5,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: Colors.white,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '75%',
    paddingBottom: 24,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  modalTitle: { fontSize: 16, fontWeight: 'bold', color: Colors.primaryText },
  modalNewBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 14,
    backgroundColor: '#F0FDF4',
    margin: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#DCFCE7',
  },
  modalNewBtnText: { fontSize: 13, fontWeight: 'bold', color: Colors.primaryForest },
  convItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 14,
    marginHorizontal: 12,
    marginVertical: 4,
    borderRadius: 10,
    backgroundColor: '#F8FAFC',
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  convItemActive: {
    borderColor: Colors.primaryForest,
    backgroundColor: '#F0FDF4',
  },
  convTitle: { fontSize: 13, fontWeight: 'bold', color: Colors.primaryText },
  convDate: { fontSize: 11, color: Colors.secondaryText, marginTop: 2 },
  micBtn: {
    backgroundColor: Colors.warmGolden,
    padding: 10,
    borderRadius: 20,
    width: 42,
    height: 42,
    alignItems: 'center',
    justifyContent: 'center',
  },
  speechContainer: {
    padding: 20,
    alignItems: 'center',
  },
  bigMicBtn: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: Colors.warmGolden,
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 12,
  },
  bigMicRecording: {
    backgroundColor: Colors.error,
  },
  speechStatus: {
    fontSize: 14,
    color: Colors.secondaryText,
    marginBottom: 16,
    textAlign: 'center',
  },
  transcriptionBox: {
    width: '100%',
    backgroundColor: Colors.softCream,
    borderRadius: 12,
    padding: 12,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  transcriptionLabel: {
    fontSize: 11,
    color: Colors.secondaryText,
    fontWeight: 'bold',
    marginBottom: 6,
  },
  transcriptionInput: {
    fontSize: 14,
    color: Colors.primaryText,
    minHeight: 60,
    textAlignVertical: 'top',
  },
  speechActions: {
    flexDirection: 'row',
    gap: 12,
    width: '100%',
  },
  cancelSpeechBtn: {
    flex: 1,
    backgroundColor: '#F1F5F9',
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
  },
  cancelSpeechText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: Colors.secondaryText,
  },
  confirmSpeechBtn: {
    flex: 1,
    backgroundColor: Colors.primaryForest,
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
  },
  confirmSpeechText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: Colors.white,
  },
});