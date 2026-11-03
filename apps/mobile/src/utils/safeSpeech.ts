/**
 * Safe wrapper for Speech synthesis (TTS)
 * Supports:
 * 1. Native ExpoSpeech (when running in compiled dev builds)
 * 2. Web SpeechSynthesis API (when running in web/browser)
 * 3. Backend Janvaani TTS via expo-av Audio player (when running in Expo Go without native ExpoSpeech)
 */

import { getExpoAudio } from './safeAudio';
import { getApiBaseUrl } from '../api/client';

export interface SpeechOptions {
  language?: string;
  pitch?: number;
  rate?: number;
  onStart?: () => void;
  onDone?: () => void;
  onStopped?: () => void;
  onError?: (error: Error) => void;
}

let NativeSpeech: any = null;

try {
  // Use require inside try-catch so Metro does not hoist it as an ES import,
  // preventing '[runtime not ready]: Error: Cannot find native module ExpoSpeech'.
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  NativeSpeech = require('expo-speech');
} catch {
  NativeSpeech = null;
}

let currentSound: any = null;

export const isNativeSpeechAvailable = (): boolean => {
  return !!(NativeSpeech && typeof NativeSpeech.speak === 'function');
};

export const stop = async (): Promise<void> => {
  if (isNativeSpeechAvailable()) {
    try {
      NativeSpeech.stop();
    } catch {}
  }
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    try {
      window.speechSynthesis.cancel();
    } catch {}
  }
  if (currentSound) {
    try {
      await currentSound.stopAsync();
      await currentSound.unloadAsync();
    } catch {}
    currentSound = null;
  }
};

export const speak = async (text: string, options?: SpeechOptions): Promise<void> => {
  await stop();

  // 1. Try Native ExpoSpeech
  if (isNativeSpeechAvailable()) {
    try {
      NativeSpeech.speak(text, {
        ...options,
        onError: (nativeErr: any) => {
          // If regional language voice is not downloaded on Android, retry with en-IN
          if (options?.language && options.language !== 'en-IN' && options.language !== 'en') {
            try {
              NativeSpeech.speak(text, {
                ...options,
                language: 'en-IN',
              });
              return;
            } catch {}
          }
          if (options?.onError) {
            options.onError(nativeErr);
          }
        },
      });
      return;
    } catch (err: any) {
      try {
        NativeSpeech.speak(text, { ...options, language: 'en-IN' });
        return;
      } catch (err2: any) {
        if (options?.onError) {
          options.onError(err2);
        }
      }
    }
  }

  // 2. Try Web SpeechSynthesis API (browser / webview)
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      if (options?.language) {
        utterance.lang = options.language;
      }
      if (options?.pitch) {
        utterance.pitch = options.pitch;
      }
      if (options?.rate) {
        utterance.rate = options.rate;
      }
      if (options?.onStart) {
        utterance.onstart = options.onStart;
      }
      if (options?.onDone) {
        utterance.onend = () => options.onDone && options.onDone();
      }
      if (options?.onError) {
        utterance.onerror = (e) =>
          options.onError && options.onError(new Error(e.error || 'Speech synthesis error'));
      }
      window.speechSynthesis.speak(utterance);
      return;
    } catch (webErr: any) {
      // Fall through to audio synthesis
    }
  }

  // 3. Fallback: Request audio synthesis from backend /speech/tts and play via expo-av
  try {
    if (options?.onStart) {
      options.onStart();
    }

    const AudioModule = getExpoAudio();
    if (!AudioModule) {
      throw new Error('Audio playback module (expo-av) is not available on this device');
    }

    await AudioModule.setAudioModeAsync({
      playsInSilentModeIOS: true,
      staysActiveInBackground: false,
    });

    const lang = options?.language ? options.language.split('-')[0] : 'en';
    const ttsUrl = `${getApiBaseUrl()}/speech/tts`;

    const response = await fetch(ttsUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'audio/wav',
      },
      body: JSON.stringify({
        text,
        language: lang,
        gender: 'male',
      }),
    });

    if (!response.ok) {
      throw new Error(`TTS server returned status ${response.status}`);
    }

    const blob = await response.blob();
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const base64Audio = (reader.result as string).split(',')[1];
        const dataUri = `data:audio/wav;base64,${base64Audio}`;

        const { sound } = await AudioModule.Sound.createAsync(
          { uri: dataUri },
          { shouldPlay: true }
        );
        currentSound = sound;

        sound.setOnPlaybackStatusUpdate((status: any) => {
          if (status.isLoaded && status.didJustFinish) {
            sound.unloadAsync();
            currentSound = null;
            if (options?.onDone) {
              options.onDone();
            }
          }
        });
      } catch (soundErr: any) {
        if (options?.onError) {
          options.onError(soundErr);
        }
      }
    };
    reader.onerror = () => {
      if (options?.onError) {
        options.onError(new Error('Failed to read synthesized audio stream'));
      }
    };
    reader.readAsDataURL(blob);
  } catch (err: any) {
    if (options?.onError) {
      options.onError(err);
    } else if (options?.onDone) {
      options.onDone();
    }
  }
};

export const isSpeakingAsync = async (): Promise<boolean> => {
  if (isNativeSpeechAvailable()) {
    try {
      return await NativeSpeech.isSpeakingAsync();
    } catch {
      return false;
    }
  }
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    return window.speechSynthesis.speaking;
  }
  if (currentSound) {
    try {
      const status = await currentSound.getStatusAsync();
      return status.isLoaded && status.isPlaying;
    } catch {
      return false;
    }
  }
  return false;
};

export default {
  speak,
  stop,
  isSpeakingAsync,
  isNativeSpeechAvailable,
};
