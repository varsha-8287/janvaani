import { NativeModules, Platform, PermissionsAndroid } from 'react-native';

/**
 * Pure Java Android Audio Recorder wrapper.
 * Completely eliminates Expo-AV native module dependencies and crashes.
 */
export const NativeAudioRecorder = NativeModules.AudioRecorder || null;

export async function requestMicrophonePermission(): Promise<boolean> {
  if (Platform.OS === 'android') {
    try {
      const granted = await PermissionsAndroid.request(
        PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
        {
          title: 'Microphone Permission',
          message: 'Janvaani needs access to your microphone to listen to your voice query in your language.',
          buttonPositive: 'OK',
        }
      );
      return granted === PermissionsAndroid.RESULTS.GRANTED;
    } catch {
      return false;
    }
  }
  return true;
}

export function isAudioRecorderAvailable(): boolean {
  return NativeAudioRecorder !== null;
}

export function getExpoAudio(): any {
  return null;
}

export function isAudioAvailable(): boolean {
  return isAudioRecorderAvailable();
}

export default {
  NativeAudioRecorder,
  requestMicrophonePermission,
  isAudioRecorderAvailable,
  getExpoAudio,
  isAudioAvailable,
};
