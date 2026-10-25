import React, { useState } from 'react';
import { View, Text, StyleSheet, FlatList, TextInput, TouchableOpacity, Image, ScrollView } from 'react-native';
import { Colors } from '../constants/colors';
import Ionicons from '@expo/vector-icons/Ionicons';

interface Props {
  onBack: () => void;
}

interface Message {
  id: string;
  sender: 'ai' | 'user';
  text: string;
  citation?: string;
}

const SUGGESTED_QUESTIONS = [
  'कौन सी योजनाएं मेरे लिए हैं?',
  'पीएम-किसान का स्टेटस क्या है?',
  'केसीसी लोन का ब्याज कितना है?',
];

export default function AIChatScreen({ onBack }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      sender: 'ai',
      text: 'नमस्ते रमेश जी! मैं आपका जनवाणी AI साथी हूँ। आप अपनी क्षेत्रीय भाषा में कृषि योजनाओं, पीएम-किसान या खाद सब्सिडी के बारे में सवाल पूछ सकते हैं।',
    },
  ]);
  const [input, setInput] = useState('');

  const handleSend = (textToSend?: string) => {
    const query = textToSend || input;
    if (!query.trim()) return;

    const userMsg: Message = { id: Date.now().toString(), sender: 'user', text: query };
    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInput('');

    // Simulate AI response with official citation
    setTimeout(() => {
      const aiReply: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: 'आपकी पात्रता जांच ली गई है। पीएम-किसान सम्मान निधि योजना के तहत अगली ₹2,000 की किस्त के लिए आपका e-KYC पूरा होना आवश्यक है।',
        citation: 'स्रोत: pmkisan.gov.in (अद्यतन: 2026)',
      };
      setMessages((prev) => [...prev, aiReply]);
    }, 1000);
  };

  return (
    <View style={styles.container}>
      {/* Top Header with Back Button & Logo */}
      <View style={styles.topHeader}>
        <TouchableOpacity style={styles.backBtn} onPress={onBack}>
          <Ionicons name="arrow-back" size={24} color={Colors.primaryText} />
        </TouchableOpacity>
        <Image source={require('../../assets/logo.png')} style={styles.logo} />
        <View>
          <Text style={styles.headerTitle}>जनवाणी AI Assistant</Text>
          <Text style={styles.headerSub}>12 भाषाओं में सहायता उपलब्ध</Text>
        </View>
      </View>

      {/* Suggested Quick Questions */}
      <View style={styles.suggestionsWrapper}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.suggestionsContainer}>
          {SUGGESTED_QUESTIONS.map((q, idx) => (
            <TouchableOpacity key={idx} style={styles.suggestChip} onPress={() => handleSend(q)}>
              <Text style={styles.suggestText}>{q}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      {/* Messages List */}
      <FlatList
        data={messages}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ padding: 16 }}
        renderItem={({ item }) => (
          <View style={[styles.bubble, item.sender === 'user' ? styles.userBubble : styles.aiBubble]}>
            <Text style={[styles.msgText, item.sender === 'user' ? styles.userText : styles.aiText]}>
              {item.text}
            </Text>
            {item.citation && (
              <View style={styles.citationBadge}>
                <Ionicons name="shield-checkmark" size={12} color={Colors.primaryForest} />
                <Text style={styles.citationText}>{item.citation}</Text>
              </View>
            )}
          </View>
        )}
      />

      {/* Input Row */}
      <View style={styles.inputRow}>
        <TouchableOpacity style={styles.micBtn}>
          <Ionicons name="mic" size={22} color="#78350F" />
        </TouchableOpacity>
        <TextInput
          style={styles.textInput}
          placeholder="सवाल लिखें या बोलें..."
          value={input}
          onChangeText={setInput}
        />
        <TouchableOpacity style={styles.sendBtn} onPress={() => handleSend()}>
          <Ionicons name="send" size={18} color={Colors.white} />
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.softCream },
  topHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    backgroundColor: Colors.white,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
    gap: 12,
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
    fontSize: 16,
    fontWeight: 'bold',
    color: Colors.primaryText,
  },
  headerSub: {
    fontSize: 11,
    color: Colors.secondaryText,
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
  bubble: { padding: 12, borderRadius: 14, marginBottom: 10, maxWidth: '82%' },
  aiBubble: { backgroundColor: Colors.white, alignSelf: 'flex-start', borderWidth: 1, borderColor: '#E2E8F0' },
  userBubble: { backgroundColor: Colors.primaryForest, alignSelf: 'flex-end' },
  msgText: { fontSize: 14, lineHeight: 20 },
  aiText: { color: Colors.primaryText },
  userText: { color: Colors.white },
  citationBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
    gap: 4,
    backgroundColor: '#DCFCE7',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
    alignSelf: 'flex-start',
  },
  citationText: {
    fontSize: 10,
    color: Colors.primaryForest,
    fontWeight: 'bold',
  },
  inputRow: { flexDirection: 'row', padding: 12, backgroundColor: Colors.white, alignItems: 'center', gap: 8 },
  micBtn: { backgroundColor: Colors.warmGolden, padding: 10, borderRadius: 20 },
  textInput: { flex: 1, backgroundColor: Colors.softCream, borderRadius: 20, paddingHorizontal: 16, height: 42 },
  sendBtn: { backgroundColor: Colors.primaryForest, padding: 10, borderRadius: 20 },
});