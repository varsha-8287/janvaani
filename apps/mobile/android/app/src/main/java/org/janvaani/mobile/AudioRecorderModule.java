package org.janvaani.mobile;

import android.media.MediaRecorder;
import android.os.Build;
import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.bridge.ReactContextBaseJavaModule;
import com.facebook.react.bridge.ReactMethod;
import com.facebook.react.bridge.Promise;
import java.io.File;
import java.io.FileInputStream;
import android.util.Base64;

public class AudioRecorderModule extends ReactContextBaseJavaModule {
    private MediaRecorder recorder;
    private String currentOutputFile;

    public AudioRecorderModule(ReactApplicationContext reactContext) {
        super(reactContext);
    }

    @Override
    public String getName() {
        return "AudioRecorder";
    }

    @ReactMethod
    public void startRecording(Promise promise) {
        try {
            if (recorder != null) {
                try {
                    recorder.stop();
                } catch (Exception ignored) {}
                recorder.release();
                recorder = null;
            }
            File cacheDir = getReactApplicationContext().getCacheDir();
            File audioFile = new File(cacheDir, "record_" + System.currentTimeMillis() + ".m4a");
            currentOutputFile = audioFile.getAbsolutePath();

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                recorder = new MediaRecorder(getReactApplicationContext());
            } else {
                recorder = new MediaRecorder();
            }
            recorder.setAudioSource(MediaRecorder.AudioSource.MIC);
            recorder.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4);
            recorder.setAudioEncoder(MediaRecorder.AudioEncoder.AAC);
            recorder.setAudioSamplingRate(16000);
            recorder.setAudioEncodingBitRate(64000);
            recorder.setOutputFile(currentOutputFile);
            recorder.prepare();
            recorder.start();
            promise.resolve(currentOutputFile);
        } catch (Exception e) {
            promise.reject("RECORDING_START_FAILED", e.getMessage(), e);
        }
    }

    @ReactMethod
    public void stopRecording(Promise promise) {
        try {
            if (recorder != null) {
                try {
                    recorder.stop();
                } catch (Exception ignored) {}
                recorder.release();
                recorder = null;
            }
            if (currentOutputFile != null) {
                File file = new File(currentOutputFile);
                if (file.exists()) {
                    byte[] bytes = new byte[(int) file.length()];
                    FileInputStream fis = new FileInputStream(file);
                    int readLen = fis.read(bytes);
                    fis.close();
                    if (readLen > 0) {
                        String base64 = Base64.encodeToString(bytes, 0, readLen, Base64.NO_WRAP);
                        promise.resolve(base64);
                        return;
                    }
                }
            }
            promise.resolve("");
        } catch (Exception e) {
            promise.reject("RECORDING_STOP_FAILED", e.getMessage(), e);
        }
    }
}

