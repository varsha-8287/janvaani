with open('apps/mobile/src/screens/DocumentVaultScreen.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update AVAILABLE_DOC_TYPES to use t(...)
old_doc_types = '''  // Available document types for uploads
  const AVAILABLE_DOC_TYPES = [
    { type: 'identity_card', label: 'Identity / Aadhaar Card', icon: 'card-outline' },
    { type: 'land_record', label: 'Land Record / Khasra', icon: 'document-text-outline' },
    { type: 'income_certificate', label: 'Income Certificate', icon: 'cash-outline' },
    { type: 'caste_certificate', label: 'Caste Certificate', icon: 'ribbon-outline' },
    { type: 'ration_card', label: 'Ration Card', icon: 'basket-outline' },
  ];'''

new_doc_types = '''  // Available document types for uploads
  const AVAILABLE_DOC_TYPES = useMemo(() => [
    { type: 'identity_card', label: t('docTypeAadhaar'), icon: 'card-outline' },
    { type: 'land_record', label: t('docTypeLandRecord'), icon: 'document-text-outline' },
    { type: 'income_certificate', label: t('docTypeIncomeCert'), icon: 'cash-outline' },
    { type: 'caste_certificate', label: t('docTypeCasteCert'), icon: 'ribbon-outline' },
    { type: 'ration_card', label: t('docTypeRationCard'), icon: 'basket-outline' },
  ], [t]);'''

# 2. Update camera & gallery options to allowsEditing: false
old_camera = '''      const res = await ImagePicker.launchCameraAsync({
        base64: true,
        quality: 0.4,
        allowsEditing: true,
        aspect: [4, 3],
      });'''

new_camera = '''      const res = await ImagePicker.launchCameraAsync({
        base64: true,
        quality: 0.4,
        allowsEditing: false,
      });'''

old_gallery = '''      const res = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        base64: true,
        quality: 0.4,
        allowsEditing: true,
        aspect: [4, 3],
      });'''

new_gallery = '''      const res = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        base64: true,
        quality: 0.4,
        allowsEditing: false,
      });'''

# 3. Update Hero Upload Button
old_hero = '''            <Text style={styles.heroUploadTitle}>+ Upload / Add Document</Text>
            <Text style={styles.heroUploadSubtitle}>
              Photograph or upload Aadhaar, Land Record, Income or Caste Certificate
            </Text>'''

new_hero = '''            <Text style={styles.heroUploadTitle}>{t('vaultUploadHeroTitle')}</Text>
            <Text style={styles.heroUploadSubtitle}>{t('vaultUploadHeroSub')}</Text>'''

# 4. Update Upload Modal Text
old_modal = '''            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Upload Document</Text>
              <TouchableOpacity onPress={() => setPickerModalVisible(false)}>
                <Ionicons name="close" size={24} color={Colors.primaryText} />
              </TouchableOpacity>
            </View>

            <ScrollView style={{ padding: 16 }}>
              {/* Document Type Selector */}
              <Text style={styles.pickerSectionTitle}>Select Document Type:</Text>'''

new_modal = '''            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>{t('uploadDocTitle')}</Text>
              <TouchableOpacity onPress={() => setPickerModalVisible(false)}>
                <Ionicons name="close" size={24} color={Colors.primaryText} />
              </TouchableOpacity>
            </View>

            <ScrollView style={{ padding: 16 }}>
              {/* Document Type Selector */}
              <Text style={styles.pickerSectionTitle}>{t('selectDocTypeTitle')}</Text>'''

old_source_opts = '''              {/* Source Options */}
              <Text style={[styles.pickerSectionTitle, { marginTop: 16 }]}>Choose Input Method:</Text>

              <TouchableOpacity
                style={styles.pickerOptionBtn}
                onPress={handlePickFromCamera}
              >
                <View style={[styles.pickerOptionIconCircle, { backgroundColor: '#DCFCE7' }]}>
                  <Ionicons name="camera" size={24} color={Colors.primaryForest} />
                </View>
                <View style={{ flex: 1, marginLeft: 12 }}>
                  <Text style={styles.pickerOptionTitle}>Take Photo with Camera</Text>
                  <Text style={styles.pickerOptionSub}>Capture document clearly using phone camera</Text>
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
                  <Text style={styles.pickerOptionTitle}>Choose from Photo Gallery</Text>
                  <Text style={styles.pickerOptionSub}>Select existing photo or scan from album</Text>
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
                  <Text style={styles.pickerOptionTitle}>Select PDF or Document File</Text>
                  <Text style={styles.pickerOptionSub}>Browse device files and upload document PDF</Text>
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
                  <Text style={styles.pickerOptionTitle}>Test with Demo Certificate</Text>
                  <Text style={styles.pickerOptionSub}>Test OCR extraction with a sample document</Text>
                </View>'''

new_source_opts = '''              {/* Source Options */}
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
                </View>'''

def replace_block(src, old, new):
    if old in src:
        return src.replace(old, new)
    elif old.replace('\n', '\r\n') in src:
        return src.replace(old.replace('\n', '\r\n'), new.replace('\n', '\r\n'))
    else:
        print('Failed to find block!')
        return src

text = replace_block(text, old_doc_types, new_doc_types)
text = replace_block(text, old_camera, new_camera)
text = replace_block(text, old_gallery, new_gallery)
text = replace_block(text, old_hero, new_hero)
text = replace_block(text, old_modal, new_modal)
text = replace_block(text, old_source_opts, new_source_opts)

with open('apps/mobile/src/screens/DocumentVaultScreen.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
print('DocumentVaultScreen.tsx successfully updated')

