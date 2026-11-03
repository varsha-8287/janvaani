import React, { useState, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Image,
  ActivityIndicator,
  Modal,
  TextInput,
  Alert,
  Platform,
  PermissionsAndroid,
  PanResponder,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import * as DocumentPicker from 'expo-document-picker';
import { Colors } from '../constants/colors';
import Ionicons from '@expo/vector-icons/Ionicons';
import { JanvaaniApi, DocumentExtractResult, ApiError } from '../api/client';
import { useAuth } from '../context/AuthContext';

interface Props {
  onBack: () => void;
}

// 1x1 transparent JPEG pixel in base64 as safe default test payload
const SAMPLE_IMAGE_BASE64 =
  '/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=';

interface VaultItem {
  id: string;
  type: string;
  title: string;
  status: string;
  icon: string;
  color: string;
  extractedData?: DocumentExtractResult;
}

export default function DocumentVaultScreen({ onBack }: Props) {
  const { profile, updateProfile, preferredLanguage, t } = useAuth();

  const [docExtractions, setDocExtractions] = useState<Record<string, DocumentExtractResult>>({});

  const vaultDocs = useMemo<VaultItem[]>(() => [
    {
      id: '1',
      type: 'identity_card',
      title: t('docIdentityTitle'),
      status: docExtractions['identity_card'] ? t('statusOcrReviewed') : t('statusSelfDeclared'),
      icon: 'card-outline',
      color: '#16A34A',
      extractedData: docExtractions['identity_card'],
    },
    {
      id: '2',
      type: 'land_record',
      title: t('docLandTitle'),
      status: docExtractions['land_record'] ? t('statusOcrReviewed') : t('statusPendingReview'),
      icon: 'document-text-outline',
      color: '#D97706',
      extractedData: docExtractions['land_record'],
    },
    {
      id: '3',
      type: 'income_certificate',
      title: t('docIncomeTitle'),
      status: docExtractions['income_certificate'] ? t('statusOcrReviewed') : t('statusReadyForOcr'),
      icon: 'cloud-upload-outline',
      color: Colors.primaryForest,
      extractedData: docExtractions['income_certificate'],
    },
    {
      id: '4',
      type: 'caste_certificate',
      title: t('docCasteTitle'),
      status: docExtractions['caste_certificate'] ? t('statusOcrReviewed') : t('statusOptional'),
      icon: 'ribbon-outline',
      color: Colors.secondaryText,
      extractedData: docExtractions['caste_certificate'],
    },
    ...(docExtractions['ration_card']
      ? [
          {
            id: '5',
            type: 'ration_card',
            title: t('docTypeRationCard'),
            status: t('statusOcrReviewed'),
            icon: 'basket-outline',
            color: '#2563EB',
            extractedData: docExtractions['ration_card'],
          },
        ]
      : []),
  ], [t, docExtractions]);

  // Available document types for uploads
  const AVAILABLE_DOC_TYPES = useMemo(() => [
    { type: 'identity_card', label: t('docTypeAadhaar'), icon: 'card-outline' },
    { type: 'land_record', label: t('docTypeLandRecord'), icon: 'document-text-outline' },
    { type: 'income_certificate', label: t('docTypeIncomeCert'), icon: 'cash-outline' },
    { type: 'caste_certificate', label: t('docTypeCasteCert'), icon: 'ribbon-outline' },
    { type: 'ration_card', label: t('docTypeRationCard'), icon: 'basket-outline' },
  ], [t]);

  // Upload Choice Modal State
  const [pickerModalVisible, setPickerModalVisible] = useState<boolean>(false);
  const [targetUploadType, setTargetUploadType] = useState<string>('income_certificate');

  // Extraction & Review Modal State
  const [selectedDoc, setSelectedDoc] = useState<VaultItem | null>(null);
  const [extracting, setExtracting] = useState<boolean>(false);
  const [extractResult, setExtractResult] = useState<DocumentExtractResult | null>(null);
  const [reviewModalVisible, setReviewModalVisible] = useState<boolean>(false);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [pendingCropAsset, setPendingCropAsset] = useState<{ uri: string; b64: string; mime: string; docType: string } | null>(null);
  const [cropRotation, setCropRotation] = useState<number>(0);
  const [cropBox, setCropBox] = useState<{ x: number; y: number; w: number; h: number }>({ x: 24, y: 50, w: 290, h: 220 });
  const [previewSize, setPreviewSize] = useState<{ width: number; height: number }>({ width: 340, height: 420 });

  // Editable fields for citizen review
  const [editableFields, setEditableFields] = useState<Record<string, string>>({});

  const openUploadPicker = (type = 'income_certificate') => {
    setTargetUploadType(type);
    setPickerModalVisible(true);
  };

  const processUploadedDocument = async (base64Data: string, mimeType: string, docType: string, cropBox?: number[], rotationDegrees?: number) => {
    const existing = vaultDocs.find((d) => d.type === docType) || {
      id: String(Date.now()),
      type: docType,
      title: docType.replace('_', ' ').toUpperCase(),
      status: 'Extracting...',
      icon: 'document-text-outline',
      color: Colors.primaryForest,
    };
    setSelectedDoc(existing);
    setExtractError(null);
    setExtracting(true);
    setReviewModalVisible(true);

    try {
      const result = await JanvaaniApi.extractDocument({
        file_base64: base64Data,
        mime_type: mimeType,
        document_type: docType,
        language: preferredLanguage || 'en',
        crop_box: cropBox,
        rotation_degrees: rotationDegrees,
      });

      setExtractResult(result);

      // Populate editable fields with extracted data
      const fieldEntries: Record<string, string> = {};
      Object.entries(result.fields || {}).forEach(([k, v]) => {
        fieldEntries[k] = v !== null && v !== undefined ? String(v) : '';
      });
      setEditableFields(fieldEntries);

      // Store in extractions map
      setDocExtractions((prev) => ({
        ...prev,
        [docType]: result,
      }));
    } catch (err: any) {
      const msg = err instanceof ApiError ? err.message : t('connectionError');
      setExtractError(msg);
    } finally {
      setExtracting(false);
    }
  };

  const dragPanResponder = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => true,
        onMoveShouldSetPanResponder: () => true,
        onPanResponderMove: (_, gestureState) => {
          setCropBox((prev) => {
            const newX = Math.max(0, Math.min(previewSize.width - prev.w, prev.x + gestureState.dx));
            const newY = Math.max(0, Math.min(previewSize.height - prev.h, prev.y + gestureState.dy));
            return { ...prev, x: newX, y: newY };
          });
        },
      }),
    [previewSize]
  );

  const resizePanResponder = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => true,
        onMoveShouldSetPanResponder: () => true,
        onPanResponderMove: (_, gestureState) => {
          setCropBox((prev) => {
            const newW = Math.max(90, Math.min(previewSize.width - prev.x, prev.w + gestureState.dx));
            const newH = Math.max(70, Math.min(previewSize.height - prev.y, prev.h + gestureState.dy));
            return { ...prev, w: newW, h: newH };
          });
        },
      }),
    [previewSize]
  );

  const handleConfirmCropAndScan = async () => {
    if (!pendingCropAsset) return;
    const { b64, mime, docType } = pendingCropAsset;
    setPendingCropAsset(null);
    const pw = Math.max(1, previewSize.width);
    const ph = Math.max(1, previewSize.height);
    const box = [
      Math.max(0, Math.min(1, cropBox.x / pw)),
      Math.max(0, Math.min(1, cropBox.y / ph)),
      Math.max(0.1, Math.min(1, cropBox.w / pw)),
      Math.max(0.1, Math.min(1, cropBox.h / ph)),
    ];
    await processUploadedDocument(b64, mime, docType, box, cropRotation);
  };

  const readAssetBase64 = async (asset: { uri: string; base64?: string | null }): Promise<string> => {
    if (asset.base64 && asset.base64.length > 20) {
      return asset.base64;
    }
    if (asset.uri) {
      const resp = await fetch(asset.uri);
      const blob = await resp.blob();
      return new Promise<string>((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => {
          const str = (reader.result as string) || '';
          resolve(str.includes(',') ? str.split(',')[1] : str);
        };
        reader.onerror = () => resolve('');
        reader.readAsDataURL(blob);
      });
    }
    return '';
  };

  const handlePickFromCamera = async () => {
    try {
      if (Platform.OS === 'android') {
        const perm = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.CAMERA);
        if (perm !== PermissionsAndroid.RESULTS.GRANTED) {
          Alert.alert(t('cameraPermTitle') || 'Permission Required', t('cameraPermMsg') || 'Camera permission is required to capture documents.');
          return;
        }
      }

      // Try camera launch; on Android release builds with cropper issues, seamlessly fallback to system media picker
      try {
        const res = await ImagePicker.launchCameraAsync({
          base64: true,
          quality: 0.5,
          allowsEditing: false,
        });

        if (!res.canceled && res.assets && res.assets[0]) {
          setPickerModalVisible(false);
          const b64 = await readAssetBase64(res.assets[0]);
          if (b64) {
            setCropRotation(0);
            setPendingCropAsset({
              uri: res.assets[0].uri,
              b64,
              mime: res.assets[0].mimeType || 'image/jpeg',
              docType: targetUploadType,
            });
          }
          return;
        }
        if (res.canceled) return;
      } catch (nativeErr: any) {
        console.warn('Native camera cropper error, falling back to system picker:', nativeErr);
        // Fallback directly to crash-free DocumentPicker
        const docRes = await DocumentPicker.getDocumentAsync({
          type: ['image/*'],
          copyToCacheDirectory: true,
        });
        if (!docRes.canceled && docRes.assets && docRes.assets[0]) {
          setPickerModalVisible(false);
          const b64 = await readAssetBase64(docRes.assets[0]);
          if (b64) {
            setCropRotation(0);
            setPendingCropAsset({
              uri: docRes.assets[0].uri,
              b64,
              mime: docRes.assets[0].mimeType || 'image/jpeg',
              docType: targetUploadType,
            });
          }
        }
      }
    } catch (err: any) {
      Alert.alert(t('cameraError') || 'Camera Error', err?.message || 'Could not launch camera');
    }
  };

  const handlePickFromGallery = async () => {
    try {
      // Direct crash-free native photo picker (bypasses broken ExponentImagePicker static initializer)
      const res = await DocumentPicker.getDocumentAsync({
        type: ['image/*'],
        copyToCacheDirectory: true,
      });

      if (!res.canceled && res.assets && res.assets[0]) {
        setPickerModalVisible(false);
        const b64 = await readAssetBase64(res.assets[0]);
        if (b64) {
          setCropRotation(0);
          setPendingCropAsset({
            uri: res.assets[0].uri,
            b64,
            mime: res.assets[0].mimeType || 'image/jpeg',
            docType: targetUploadType,
          });
        }
      }
    } catch (err: any) {
      Alert.alert(t('galleryError') || 'Gallery Error', err?.message || 'Could not pick image');
    }
  };

  const handlePickDocumentFile = async () => {
    try {
      const res = await DocumentPicker.getDocumentAsync({
        type: ['application/pdf', 'image/*'],
        copyToCacheDirectory: true,
      });
      if (!res.canceled && res.assets && res.assets[0]) {
        const asset = res.assets[0];
        setPickerModalVisible(false);
        const b64 = await readAssetBase64(asset);
        if (b64) {
          if (asset.mimeType?.startsWith('image/')) {
            setCropRotation(0);
            setPendingCropAsset({
              uri: asset.uri,
              b64,
              mime: asset.mimeType || 'image/jpeg',
              docType: targetUploadType,
            });
          } else {
            await processUploadedDocument(
              b64,
              asset.mimeType || 'application/pdf',
              targetUploadType
            );
          }
        }
      }
    } catch (err: any) {
      Alert.alert(t('fileError'), err?.message || 'Could not read document');
    }
  };

  const handleTestSample = async () => {
    setPickerModalVisible(false);
    await processUploadedDocument(SAMPLE_IMAGE_BASE64, 'image/jpeg', targetUploadType);
  };

  const handleApplyToProfile = async () => {
    if (!editableFields || Object.keys(editableFields).length === 0) {
      setReviewModalVisible(false);
      return;
    }

    try {
      const newAttributes = {
        ...(profile?.attributes || {}),
        ...editableFields,
      };

      await updateProfile({
        attributes: newAttributes,
      });

      Alert.alert(
        t('success'),
        t('ocrSavedSuccess')
      );
      setReviewModalVisible(false);
    } catch (err: any) {
      Alert.alert(t('connectionError'), err?.message || 'Failed to save details to profile.');
    }
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
          <Text style={styles.headerTitle}>{t('vaultHeaderTitle')}</Text>
          <Text style={styles.subTitleHeader}>{t('vaultHeaderSub')}</Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={{ padding: 16 }}>
        <Text style={styles.sectionDesc}>
          {t('vaultDesc')}
        </Text>

        {/* Prominent "+ Upload Document" Action Banner */}
        <TouchableOpacity
          style={styles.heroUploadBtn}
          onPress={() => openUploadPicker('income_certificate')}
        >
          <View style={styles.heroUploadIconCircle}>
            <Ionicons name="cloud-upload" size={24} color={Colors.white} />
          </View>
          <View style={{ flex: 1, marginLeft: 12 }}>
            <Text style={styles.heroUploadTitle}>{t('vaultUploadHeroTitle')}</Text>
            <Text style={styles.heroUploadSubtitle}>{t('vaultUploadHeroSub')}</Text>
          </View>
          <Ionicons name="chevron-forward" size={20} color={Colors.primaryForest} />
        </TouchableOpacity>

        {vaultDocs.map((doc) => (
          <View key={doc.id} style={styles.docCard}>
            <Ionicons name={doc.icon as any} size={28} color={doc.color} />
            <View style={{ flex: 1, marginLeft: 12 }}>
              <Text style={styles.docTitle}>{doc.title}</Text>
              <Text style={[styles.docStatus, { color: doc.color }]}>{doc.status}</Text>
            </View>
            <TouchableOpacity
              style={styles.uploadBtn}
              onPress={() => openUploadPicker(doc.type)}
            >
              <Ionicons name="camera-outline" size={20} color={Colors.primaryForest} />
            </TouchableOpacity>
          </View>
        ))}

        {/* Strict Legal & Privacy Disclaimer */}
        <View style={styles.privacyCard}>
          <Ionicons name="shield-checkmark-outline" size={20} color={Colors.primaryForest} />
          <Text style={styles.privacyText}>
            {t('legalDisclaimer')}
          </Text>
        </View>
      </ScrollView>

      {/* OCR Review & Correction Modal */}
      <Modal visible={reviewModalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>
                {t('ocrReviewTitle')} ({selectedDoc?.title})
              </Text>
              <TouchableOpacity onPress={() => setReviewModalVisible(false)}>
                <Ionicons name="close" size={24} color={Colors.primaryText} />
              </TouchableOpacity>
            </View>

            <ScrollView style={{ padding: 16 }}>
              {extracting && (
                <View style={styles.centerBox}>
                  <ActivityIndicator size="large" color={Colors.primaryForest} />
                  <Text style={styles.statusText}>
                    {t('ocrProgress')}
                  </Text>
                </View>
              )}

              {extractError && (
                <View style={styles.errorBanner}>
                  <Ionicons name="alert-circle" size={20} color={Colors.error} />
                  <Text style={styles.errorBannerText}>{extractError}</Text>
                </View>
              )}

              {extractResult && !extracting && (
                <View>
                  {/* Non-Authentic Alert Badge */}
                  <View style={styles.unverifiedBanner}>
                    <Ionicons name="warning-outline" size={20} color="#B45309" />
                    <View style={{ flex: 1 }}>
                      <Text style={styles.unverifiedTitle}>
                        {t('reviewRequiredTitle')}
                      </Text>
                      <Text style={styles.unverifiedSub}>
                        Provider: {extractResult.provider} • authenticity_verified: false
                      </Text>
                    </View>
                  </View>

                  {/* Validation & Conflict Warnings */}
                  {extractResult.profile_conflicts && extractResult.profile_conflicts.length > 0 && (
                    <View style={styles.conflictCard}>
                      <Text style={styles.conflictTitle}>{t('profileConflictsTitle')}</Text>
                      {extractResult.profile_conflicts.map((issue, idx) => (
                        <Text key={idx} style={styles.conflictText}>
                          ⚠️ {issue.field}: {issue.message}
                        </Text>
                      ))}
                    </View>
                  )}

                  {/* Citizen Correction Fields */}
                  <Text style={styles.formSectionTitle}>
                    {t('reviewFieldsTitle')}
                  </Text>
                  {Object.entries(editableFields).length === 0 ? (
                    <Text style={styles.emptyFieldsText}>{t('noFieldsDetected')}</Text>
                  ) : (
                    Object.entries(editableFields).map(([key, val]) => (
                      <View key={key} style={styles.fieldRow}>
                        <Text style={styles.fieldLabel}>{key}:</Text>
                        <TextInput
                          style={styles.fieldInput}
                          value={val}
                          onChangeText={(newVal) =>
                            setEditableFields((prev) => ({ ...prev, [key]: newVal }))
                          }
                        />
                      </View>
                    ))
                  )}

                  {/* Extracted Raw Text Preview */}
                  {extractResult.raw_text && (
                    <View style={styles.rawTextBox}>
                      <Text style={styles.rawTextTitle}>{t('rawTextTitle')}</Text>
                      <Text style={styles.rawTextContent} numberOfLines={4}>
                        {extractResult.raw_text}
                      </Text>
                    </View>
                  )}

                  {/* Actions */}
                  <View style={styles.modalActions}>
                    <TouchableOpacity
                      style={styles.cancelBtn}
                      onPress={() => setReviewModalVisible(false)}
                    >
                      <Text style={styles.cancelBtnText}>{t('cancel')}</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={styles.applyBtn}
                      onPress={handleApplyToProfile}
                    >
                      <Ionicons name="save-outline" size={16} color={Colors.white} />
                      <Text style={styles.applyBtnText}>{t('saveAndVerify')}</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              )}
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* Pure Cropping Grid Modal (Shows immediately after photo capture) */}
      <Modal visible={!!pendingCropAsset} animationType="slide" transparent={false}>
        <View style={styles.cropScreenContainer}>
          {/* Header */}
          <View style={styles.cropTopBar}>
            <TouchableOpacity onPress={() => setPendingCropAsset(null)} style={styles.cropIconButton}>
              <Ionicons name="close" size={26} color="#FFFFFF" />
            </TouchableOpacity>
            <Text style={styles.cropHeaderTitle}>Crop Document</Text>
            <TouchableOpacity
              onPress={() => setCropRotation((prev) => (prev + 90) % 360)}
              style={styles.cropIconButton}
            >
              <Ionicons name="refresh" size={24} color="#FFFFFF" />
            </TouchableOpacity>
          </View>

          {/* Interactive Photo & 3x3 Cropping Grid Stage */}
          <View
            style={styles.cropStage}
            onLayout={(e) => {
              const { width, height } = e.nativeEvent.layout;
              if (width > 0 && height > 0) {
                setPreviewSize({ width, height });
              }
            }}
          >
            {pendingCropAsset && (
              <Image
                source={{ uri: pendingCropAsset.uri }}
                style={[
                  styles.cropStageImage,
                  { transform: [{ rotate: `${cropRotation}deg` }] }
                ]}
                resizeMode="contain"
              />
            )}

            {/* Draggable Crop Box with Rule-of-Thirds 3x3 Grid */}
            <View
              {...dragPanResponder.panHandlers}
              style={[
                styles.cropGridBox,
                {
                  left: cropBox.x,
                  top: cropBox.y,
                  width: cropBox.w,
                  height: cropBox.h,
                },
              ]}
            >
              {/* 3x3 Grid Lines */}
              <View style={[styles.gridLineV, { left: '33.33%' }]} pointerEvents="none" />
              <View style={[styles.gridLineV, { left: '66.66%' }]} pointerEvents="none" />
              <View style={[styles.gridLineH, { top: '33.33%' }]} pointerEvents="none" />
              <View style={[styles.gridLineH, { top: '66.66%' }]} pointerEvents="none" />

              {/* Corner Handles */}
              <View style={[styles.gridCorner, styles.gCornerTL]} pointerEvents="none" />
              <View style={[styles.gridCorner, styles.gCornerTR]} pointerEvents="none" />
              <View style={[styles.gridCorner, styles.gCornerBL]} pointerEvents="none" />
              <View
                {...resizePanResponder.panHandlers}
                style={[styles.gridCorner, styles.gCornerBR, styles.resizeTouchTarget]}
              />
            </View>
          </View>

          {/* Bottom Toolbar: Cancel & Done */}
          <View style={styles.cropBottomBar}>
            <TouchableOpacity
              style={styles.cropCancelPill}
              onPress={() => setPendingCropAsset(null)}
            >
              <Ionicons name="close-circle-outline" size={20} color="#94A3B8" />
              <Text style={styles.cropCancelPillText}>Cancel</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.cropDonePill}
              onPress={handleConfirmCropAndScan}
            >
              <Ionicons name="checkmark-circle" size={20} color="#FFFFFF" />
              <Text style={styles.cropDonePillText}>Crop & Scan</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* Upload Source & Document Type Selection Modal */}
      <Modal visible={pickerModalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.pickerModalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>{t('uploadDocTitle')}</Text>
              <TouchableOpacity onPress={() => setPickerModalVisible(false)}>
                <Ionicons name="close" size={24} color={Colors.primaryText} />
              </TouchableOpacity>
            </View>

            <ScrollView style={{ padding: 16 }}>
              {/* Document Type Selector */}
              <Text style={styles.pickerSectionTitle}>{t('selectDocTypeTitle')}</Text>
              <View style={styles.docTypeChipsContainer}>
                {AVAILABLE_DOC_TYPES.map((dt) => {
                  const isSelected = targetUploadType === dt.type;
                  return (
                    <TouchableOpacity
                      key={dt.type}
                      style={[styles.docTypeChip, isSelected && styles.docTypeChipActive]}
                      onPress={() => setTargetUploadType(dt.type)}
                    >
                      <Ionicons
                        name={dt.icon as any}
                        size={16}
                        color={isSelected ? Colors.white : Colors.primaryForest}
                      />
                      <Text
                        style={[
                          styles.docTypeChipText,
                          isSelected && styles.docTypeChipTextActive,
                        ]}
                      >
                        {dt.label}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>

              {/* Source Options */}
              <Text style={[styles.pickerSectionTitle, { marginTop: 16 }]}>{t('chooseInputMethodTitle')}</Text>

              <TouchableOpacity
                style={styles.pickerOptionBtn}
                onPress={handlePickFromCamera}
              >
                <View style={[styles.pickerOptionIconCircle, { backgroundColor: '#DCFCE7' }]}>
                  <Ionicons name="camera" size={24} color={Colors.primaryForest} />
                </View>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={styles.pickerOptionTitle}>{t('takePhotoTitle')}</Text>
                  <Text style={styles.pickerOptionSub}>{t('takePhotoSub')}</Text>
                </View>
                <Ionicons name="chevron-forward" size={18} color={Colors.secondaryText} />
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.pickerOptionBtn}
                onPress={handlePickFromGallery}
              >
                <View style={[styles.pickerOptionIconCircle, { backgroundColor: '#DBEAFE' }]}>
                  <Ionicons name="images" size={24} color="#2563EB" />
                </View>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={styles.pickerOptionTitle}>{t('chooseGalleryTitle')}</Text>
                  <Text style={styles.pickerOptionSub}>{t('chooseGallerySub')}</Text>
                </View>
                <Ionicons name="chevron-forward" size={18} color={Colors.secondaryText} />
              </TouchableOpacity>

              <TouchableOpacity
                style={styles.pickerOptionBtn}
                onPress={handlePickDocumentFile}
              >
                <View style={[styles.pickerOptionIconCircle, { backgroundColor: '#FEF3C7' }]}>
                  <Ionicons name="document-attach" size={24} color="#D97706" />
                </View>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={styles.pickerOptionTitle}>{t('selectPdfTitle')}</Text>
                  <Text style={styles.pickerOptionSub}>{t('selectPdfSub')}</Text>
                </View>
                <Ionicons name="chevron-forward" size={18} color={Colors.secondaryText} />
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.pickerOptionBtn, { borderColor: '#E2E8F0', backgroundColor: '#F8FAFC' }]}
                onPress={handleTestSample}
              >
                <View style={[styles.pickerOptionIconCircle, { backgroundColor: '#F1F5F9' }]}>
                  <Ionicons name="flask-outline" size={24} color={Colors.secondaryText} />
                </View>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={styles.pickerOptionTitle}>{t('pickSampleTitle')}</Text>
                  <Text style={styles.pickerOptionSub}>{t('pickSampleSub')}</Text>
                </View>
                <Ionicons name="chevron-forward" size={18} color={Colors.secondaryText} />
              </TouchableOpacity>
            </ScrollView>
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
  subTitleHeader: {
    fontSize: 11,
    color: Colors.secondaryText,
  },
  sectionDesc: {
    fontSize: 13,
    color: Colors.secondaryText,
    marginBottom: 16,
    lineHeight: 18,
  },
  docCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.white,
    padding: 16,
    borderRadius: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  docTitle: { fontSize: 14, fontWeight: 'bold', color: Colors.primaryText },
  docStatus: { fontSize: 12, marginTop: 2, fontWeight: '500' },
  uploadBtn: { padding: 8, backgroundColor: '#F0FDF4', borderRadius: 8 },
  privacyCard: {
    flexDirection: 'row',
    backgroundColor: '#F0FDF4',
    borderColor: Colors.secondaryLeaf,
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    marginTop: 12,
    alignItems: 'center',
    gap: 10,
  },
  privacyText: {
    flex: 1,
    fontSize: 11,
    color: Colors.primaryForest,
    lineHeight: 16,
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
    maxHeight: '85%',
    paddingBottom: 20,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  modalTitle: { fontSize: 16, fontWeight: 'bold', color: Colors.primaryText, flex: 1, marginRight: 8 },
  centerBox: { alignItems: 'center', padding: 24 },
  statusText: { fontSize: 13, color: Colors.secondaryText, marginTop: 8 },
  errorBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#FEE2E2',
    padding: 12,
    borderRadius: 8,
    marginBottom: 12,
  },
  errorBannerText: { color: Colors.error, fontSize: 12, flex: 1 },
  unverifiedBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: '#FEF3C7',
    padding: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#FDE68A',
    marginBottom: 14,
  },
  unverifiedTitle: { fontSize: 13, fontWeight: 'bold', color: '#B45309' },
  unverifiedSub: { fontSize: 11, color: '#92400E', marginTop: 2 },
  conflictCard: {
    backgroundColor: '#FEE2E2',
    padding: 10,
    borderRadius: 8,
    marginBottom: 12,
  },
  conflictTitle: { fontSize: 12, fontWeight: 'bold', color: Colors.error, marginBottom: 4 },
  conflictText: { fontSize: 11, color: '#991B1B' },
  formSectionTitle: { fontSize: 13, fontWeight: 'bold', color: Colors.primaryForest, marginBottom: 8 },
  emptyFieldsText: { fontSize: 12, color: Colors.secondaryText, fontStyle: 'italic', marginVertical: 8 },
  fieldRow: { marginBottom: 10 },
  fieldLabel: { fontSize: 12, fontWeight: '600', color: Colors.primaryText, marginBottom: 4 },
  fieldInput: {
    backgroundColor: Colors.softCream,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    fontSize: 13,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  rawTextBox: {
    backgroundColor: '#F8FAFC',
    padding: 10,
    borderRadius: 8,
    marginVertical: 10,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  rawTextTitle: { fontSize: 11, fontWeight: 'bold', color: Colors.secondaryText },
  rawTextContent: { fontSize: 11, color: Colors.secondaryText, marginTop: 4 },
  modalActions: { flexDirection: 'row', gap: 10, marginTop: 14 },
  cancelBtn: {
    flex: 1,
    backgroundColor: '#F1F5F9',
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  cancelBtnText: { color: Colors.secondaryText, fontWeight: 'bold', fontSize: 13 },
  applyBtn: {
    flex: 2,
    flexDirection: 'row',
    gap: 6,
    backgroundColor: Colors.primaryForest,
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  applyBtnText: { color: Colors.white, fontWeight: 'bold', fontSize: 13 },
  heroUploadBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F0FDF4',
    borderWidth: 1.5,
    borderColor: Colors.secondaryLeaf,
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    shadowColor: Colors.primaryForest,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
  heroUploadIconCircle: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: Colors.primaryForest,
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroUploadTitle: {
    fontSize: 15,
    fontWeight: 'bold',
    color: Colors.primaryForest,
  },
  heroUploadSubtitle: {
    fontSize: 11,
    color: Colors.secondaryText,
    marginTop: 2,
    lineHeight: 15,
  },
  pickerModalContent: {
    backgroundColor: Colors.white,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '85%',
    paddingBottom: 24,
  },
  pickerSectionTitle: {
    fontSize: 13,
    fontWeight: 'bold',
    color: Colors.primaryText,
    marginBottom: 8,
  },
  docTypeChipsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 8,
  },
  docTypeChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    backgroundColor: Colors.softCream,
  },
  docTypeChipActive: {
    backgroundColor: Colors.primaryForest,
    borderColor: Colors.primaryForest,
  },
  docTypeChipText: {
    fontSize: 12,
    color: Colors.primaryText,
    fontWeight: '500',
  },
  docTypeChipTextActive: {
    color: Colors.white,
    fontWeight: 'bold',
  },
  pickerOptionBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    backgroundColor: Colors.white,
    marginBottom: 10,
  },
  pickerOptionIconCircle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pickerOptionTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: Colors.primaryText,
  },
  pickerOptionSub: {
    fontSize: 11,
    color: Colors.secondaryText,
    marginTop: 2,
  },
    cropScreenContainer: {
    flex: 1,
    backgroundColor: '#000000',
  },
  cropTopBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 44,
    paddingBottom: 12,
    backgroundColor: '#000000',
  },
  cropHeaderTitle: {
    color: '#FFFFFF',
    fontSize: 17,
    fontWeight: 'bold',
  },
  cropIconButton: {
    padding: 8,
  },
  cropStage: {
    flex: 1,
    position: 'relative',
    backgroundColor: '#0B0F19',
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  cropStageImage: {
    width: '100%',
    height: '100%',
  },
  cropGridBox: {
    position: 'absolute',
    borderWidth: 2,
    borderColor: '#22C55E',
    backgroundColor: 'rgba(34, 197, 94, 0.08)',
  },
  gridLineV: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    width: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.4)',
  },
  gridLineH: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.4)',
  },
  gridCorner: {
    position: 'absolute',
    width: 18,
    height: 18,
    borderColor: '#4ADE80',
  },
  gCornerTL: {
    top: -2,
    left: -2,
    borderTopWidth: 3.5,
    borderLeftWidth: 3.5,
  },
  gCornerTR: {
    top: -2,
    right: -2,
    borderTopWidth: 3.5,
    borderRightWidth: 3.5,
  },
  gCornerBL: {
    bottom: -2,
    left: -2,
    borderBottomWidth: 3.5,
    borderLeftWidth: 3.5,
  },
  gCornerBR: {
    bottom: -2,
    right: -2,
    borderBottomWidth: 3.5,
    borderRightWidth: 3.5,
  },
  resizeTouchTarget: {
    width: 36,
    height: 36,
    bottom: -8,
    right: -8,
  },
  cropBottomBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 32,
    backgroundColor: '#000000',
    gap: 16,
  },
  cropCancelPill: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: '#1E293B',
    paddingVertical: 14,
    borderRadius: 24,
  },
  cropCancelPillText: {
    color: '#94A3B8',
    fontSize: 14,
    fontWeight: 'bold',
  },
  cropDonePill: {
    flex: 1.5,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: '#16A34A',
    paddingVertical: 14,
    borderRadius: 24,
  },
  cropDonePillText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: 'bold',
  },

});
