import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Image,
  ActivityIndicator,
  TextInput,
  Alert,
} from 'react-native';
import { Colors } from '../constants/colors';
import Ionicons from '@expo/vector-icons/Ionicons';
import { useAuth } from '../context/AuthContext';

interface Props {
  onBack: () => void;
  onSelectLanguage?: () => void;
}

export default function ProfileScreen({ onBack, onSelectLanguage }: Props) {
  const { profile, isLoading, error, isAuthenticated, token, logout, login, refreshProfile, updateProfile, preferredLanguage, t } = useAuth();
  
  const [isEditing, setIsEditing] = useState(false);
  const [nameInput, setNameInput] = useState('');
  const [stateInput, setStateInput] = useState('');
  const [districtInput, setDistrictInput] = useState('');
  const [farmerCatInput, setFarmerCatInput] = useState('');
  const [landInput, setLandInput] = useState('');
  const [incomeInput, setIncomeInput] = useState('');
  const [ageInput, setAgeInput] = useState('');
  const [genderInput, setGenderInput] = useState('');
  const [casteInput, setCasteInput] = useState('');
  const [isBplInput, setIsBplInput] = useState<'yes' | 'no'>('no');
  const [isTaxPayerInput, setIsTaxPayerInput] = useState<'yes' | 'no'>('no');
  const [isGovtEmployeeInput, setIsGovtEmployeeInput] = useState<'yes' | 'no'>('no');
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const startEditing = () => {
    setNameInput(profile?.attributes?.name || '');
    setStateInput(profile?.state || 'Madhya Pradesh');
    setDistrictInput(profile?.district || 'Sehore');
    setFarmerCatInput(profile?.attributes?.farmer_category || 'small_farmer');
    setLandInput(profile?.attributes?.land_hectares !== undefined ? String(profile.attributes.land_hectares) : '1.5');
    setIncomeInput(profile?.attributes?.annual_income !== undefined ? String(profile.attributes.annual_income) : '120000');
    setAgeInput(profile?.attributes?.age !== undefined ? String(profile.attributes.age) : '42');
    setGenderInput(profile?.attributes?.gender || 'male');
    setCasteInput(profile?.attributes?.caste_category || 'OBC');
    setIsBplInput(profile?.attributes?.is_bpl ? 'yes' : 'no');
    setIsTaxPayerInput(profile?.attributes?.is_income_tax_payer ? 'yes' : 'no');
    setIsGovtEmployeeInput(profile?.attributes?.is_serving_or_retired_govt_employee ? 'yes' : 'no');
    setSaveError(null);
    setIsEditing(true);
  };

  const handleSave = async () => {
    setIsSaving(true);
    setSaveError(null);
    try {
      const parsedLand = landInput.trim() ? parseFloat(landInput) : undefined;
      const parsedIncome = incomeInput.trim() ? parseFloat(incomeInput) : undefined;
      const parsedAge = ageInput.trim() ? parseInt(ageInput, 10) : undefined;

      const isLandholdingFarmer =
        parsedLand !== undefined && !isNaN(parsedLand)
          ? parsedLand > 0
          : Boolean(farmerCatInput && !farmerCatInput.toLowerCase().includes('landless') && !farmerCatInput.toLowerCase().includes('not'));

      const isTaxPayer = isTaxPayerInput === 'yes' || (isTaxPayerInput === 'no' ? false : (parsedIncome !== undefined && parsedIncome > 250000));
      const isGovtEmployee = isGovtEmployeeInput === 'yes';
      const isBpl = isBplInput === 'yes';

      const newAttributes: Record<string, any> = {
        ...(profile?.attributes || {}),
        name: nameInput.trim() || profile?.attributes?.name || undefined,
        farmer_category: farmerCatInput.trim() || 'small_farmer',
        land_hectares: parsedLand !== undefined && !isNaN(parsedLand) ? parsedLand : 1.5,
        annual_income: parsedIncome !== undefined && !isNaN(parsedIncome) ? parsedIncome : 120000,
        age: parsedAge !== undefined && !isNaN(parsedAge) ? parsedAge : 42,
        gender: genderInput.trim() || 'male',
        caste_category: casteInput.trim() || 'OBC',
        is_landholding_farmer: isLandholdingFarmer,
        is_income_tax_payer: isTaxPayer,
        is_institutional_landholder: false,
        is_serving_or_retired_govt_employee: isGovtEmployee,
        is_bpl: isBpl,
        has_savings_bank_account: true,
      };

      // Clean undefined keys
      Object.keys(newAttributes).forEach((key) => {
        if (newAttributes[key] === undefined) delete newAttributes[key];
      });

      await updateProfile({
        state: stateInput.trim() || null,
        district: districtInput.trim() || null,
        attributes: newAttributes,
      });
      setIsEditing(false);
    } catch (err: any) {
      setSaveError(err?.message || 'Failed to update profile');
    } finally {
      setIsSaving(false);
    }
  };

  const displayName = profile?.attributes?.name || t('greetingCitizen');
  const displayLocation = [profile?.district, profile?.state].filter(Boolean).join(', ') || t('locationNotSet');
  const displayCategory = profile?.attributes?.farmer_category || t('farmerCategoryNotSet');

  const ATTRIBUTE_LABELS: Record<string, string> = {
    name: t('attrCitizenName'),
    farmer_category: t('attrFarmerCategory'),
    land_hectares: t('attrLandHolding'),
    annual_income: t('attrIncome'),
    age: t('attrAge'),
    gender: t('attrGender'),
    caste_category: t('attrSocialCategory'),
    is_landholding_farmer: t('attrLandholdingFarmer'),
    is_income_tax_payer: t('attrTaxPayer'),
    is_institutional_landholder: t('attrInstitutionalLandholder'),
    is_serving_or_retired_govt_employee: t('attrGovtEmployee'),
    is_bpl: t('attrBpl'),
    has_savings_bank_account: t('attrBankAccount'),
  };

  return (
    <View style={styles.container}>
      {/* Top Header with Back Button & Logo */}
      <View style={styles.topHeader}>
        <TouchableOpacity style={styles.backBtn} onPress={onBack}>
          <Ionicons name="arrow-back" size={24} color={Colors.primaryText} />
        </TouchableOpacity>
        <Image source={require('../../assets/logo.png')} style={styles.logo} />
        <View style={{ flex: 1 }}>
          <Text style={styles.headerTitle}>{t('profileHeaderTitle')}</Text>
          <Text style={styles.subTitleHeader}>{t('profileHeaderSub')}</Text>
        </View>
        <TouchableOpacity style={styles.refreshBtn} onPress={refreshProfile}>
          <Ionicons name="refresh" size={20} color={Colors.primaryForest} />
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={{ padding: 16 }}>
        {/* Loading / Error States */}
        {isLoading && !isEditing && (
          <View style={styles.loadingBanner}>
            <ActivityIndicator size="small" color={Colors.primaryForest} />
            <Text style={styles.loadingText}>{t('loadingProfile')}</Text>
          </View>
        )}

        {error && (
          <View style={styles.errorCard}>
            <Ionicons name="alert-circle-outline" size={20} color={Colors.error} />
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        {/* Profile Card Header */}
        <View style={styles.profileHeaderCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>
              {displayName.charAt(0).toUpperCase()}
            </Text>
          </View>
          <Text style={styles.userName}>{displayName}</Text>
          <Text style={styles.userPhone}>
            {token ? `${t('sessionLabel')}: ${token.substring(0, 15)}...` : t('notLoggedIn')}
          </Text>
          <Text style={styles.userMeta}>{displayLocation} • {displayCategory}</Text>

          <View style={styles.verifiedBadge}>
            <Ionicons name="shield-checkmark" size={14} color="#16A34A" />
            <Text style={styles.verifiedText}>
              {profile ? t('profileActiveStatus') : t('profilePendingStatus')}
            </Text>
          </View>

          {!isEditing && (
            <TouchableOpacity style={styles.editBtn} onPress={startEditing}>
              <Ionicons name="create-outline" size={16} color={Colors.primaryForest} />
              <Text style={styles.editBtnText}>{t('editProfileBtn')}</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Profile Edit Form */}
        {isEditing && (
          <View style={styles.editCard}>
            <Text style={styles.editTitle}>{t('editDetailsTitle')}</Text>
            {saveError && <Text style={styles.saveErrorText}>{saveError}</Text>}

            <Text style={styles.inputLabel}>{t('fullNameLabel')}</Text>
            <TextInput
              style={styles.input}
              placeholder={t('placeholderName')}
              value={nameInput}
              onChangeText={setNameInput}
            />

            <Text style={styles.inputLabel}>{t('stateLabel')}</Text>
            <TextInput
              style={styles.input}
              placeholder={t('placeholderState')}
              value={stateInput}
              onChangeText={setStateInput}
            />

            <Text style={styles.inputLabel}>{t('districtLabel')}</Text>
            <TextInput
              style={styles.input}
              placeholder={t('placeholderDistrict')}
              value={districtInput}
              onChangeText={setDistrictInput}
            />

            <Text style={styles.inputLabel}>{t('farmerCategoryLabel')}</Text>
            <TextInput
              style={styles.input}
              placeholder={t('placeholderFarmerCat')}
              value={farmerCatInput}
              onChangeText={setFarmerCatInput}
            />

            <Text style={styles.inputLabel}>{t('landHectaresLabel')}</Text>
            <TextInput
              style={styles.input}
              placeholder={t('placeholderLand')}
              keyboardType="numeric"
              value={landInput}
              onChangeText={setLandInput}
            />

            <Text style={styles.inputLabel}>{t('annualIncomeLabel')}</Text>
            <TextInput
              style={styles.input}
              placeholder={t('placeholderIncome')}
              keyboardType="numeric"
              value={incomeInput}
              onChangeText={setIncomeInput}
            />

            <Text style={styles.inputLabel}>{t('ageLabel')}</Text>
            <TextInput
              style={styles.input}
              placeholder={t('placeholderAge')}
              keyboardType="numeric"
              value={ageInput}
              onChangeText={setAgeInput}
            />

            <Text style={styles.inputLabel}>{t('genderLabel')}</Text>
            <TextInput
              style={styles.input}
              placeholder={t('placeholderGender')}
              value={genderInput}
              onChangeText={setGenderInput}
            />

            <Text style={styles.inputLabel}>{t('casteCategoryLabel')}</Text>
            <TextInput
              style={styles.input}
              placeholder={t('placeholderCaste')}
              value={casteInput}
              onChangeText={setCasteInput}
            />

            {/* Quick Toggle Chips for Boolean Eligibility Fields */}
            <View style={{ marginTop: 12 }}>
              <Text style={styles.inputLabel}>{t('bplQuestion')}</Text>
              <View style={{ flexDirection: 'row', gap: 10, marginTop: 4 }}>
                <TouchableOpacity
                  style={[styles.toggleChip, isBplInput === 'yes' && styles.toggleChipActive]}
                  onPress={() => setIsBplInput('yes')}
                >
                  <Text style={[styles.toggleChipText, isBplInput === 'yes' && styles.toggleChipTextActive]}>{t('yesChip')}</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.toggleChip, isBplInput === 'no' && styles.toggleChipActive]}
                  onPress={() => setIsBplInput('no')}
                >
                  <Text style={[styles.toggleChipText, isBplInput === 'no' && styles.toggleChipTextActive]}>{t('noChip')}</Text>
                </TouchableOpacity>
              </View>
            </View>

            <View style={{ marginTop: 10 }}>
              <Text style={styles.inputLabel}>{t('taxPayerQuestion')}</Text>
              <View style={{ flexDirection: 'row', gap: 10, marginTop: 4 }}>
                <TouchableOpacity
                  style={[styles.toggleChip, isTaxPayerInput === 'yes' && styles.toggleChipActive]}
                  onPress={() => setIsTaxPayerInput('yes')}
                >
                  <Text style={[styles.toggleChipText, isTaxPayerInput === 'yes' && styles.toggleChipTextActive]}>{t('yesChip')}</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.toggleChip, isTaxPayerInput === 'no' && styles.toggleChipActive]}
                  onPress={() => setIsTaxPayerInput('no')}
                >
                  <Text style={[styles.toggleChipText, isTaxPayerInput === 'no' && styles.toggleChipTextActive]}>{t('noChip')}</Text>
                </TouchableOpacity>
              </View>
            </View>

            <View style={{ marginTop: 10 }}>
              <Text style={styles.inputLabel}>{t('govtEmployeeQuestion')}</Text>
              <View style={{ flexDirection: 'row', gap: 10, marginTop: 4 }}>
                <TouchableOpacity
                  style={[styles.toggleChip, isGovtEmployeeInput === 'yes' && styles.toggleChipActive]}
                  onPress={() => setIsGovtEmployeeInput('yes')}
                >
                  <Text style={[styles.toggleChipText, isGovtEmployeeInput === 'yes' && styles.toggleChipTextActive]}>{t('yesChip')}</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.toggleChip, isGovtEmployeeInput === 'no' && styles.toggleChipActive]}
                  onPress={() => setIsGovtEmployeeInput('no')}
                >
                  <Text style={[styles.toggleChipText, isGovtEmployeeInput === 'no' && styles.toggleChipTextActive]}>{t('noChip')}</Text>
                </TouchableOpacity>
              </View>
            </View>

            <View style={styles.editActions}>
              <TouchableOpacity
                style={styles.cancelBtn}
                onPress={() => setIsEditing(false)}
                disabled={isSaving}
              >
                <Text style={styles.cancelBtnText}>{t('cancel')}</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.saveBtn}
                onPress={handleSave}
                disabled={isSaving}
              >
                {isSaving ? (
                  <ActivityIndicator color={Colors.white} />
                ) : (
                  <Text style={styles.saveBtnText}>{t('saveProfileBtn')}</Text>
                )}
              </TouchableOpacity>
            </View>
          </View>
        )}

        {/* Attributes Summary Card */}
        {profile?.attributes && Object.keys(profile.attributes).length > 0 && !isEditing && (
          <View style={styles.detailsCard}>
            <Text style={styles.detailsCardTitle}>{t('registeredAttrsTitle')}</Text>
            {Object.entries(profile.attributes).map(([key, value]) => (
              <View key={key} style={styles.detailRow}>
                <Text style={styles.detailKey}>{ATTRIBUTE_LABELS[key] || key.replace(/_/g, ' ')}:</Text>
                <Text style={styles.detailVal}>
                  {value === true ? t('yesChip') : value === false ? t('noChip') : String(value)}
                </Text>
              </View>
            ))}
          </View>
        )}

        {/* Settings Menu Options */}
        <View style={styles.menuGroup}>
          <TouchableOpacity style={styles.menuItem} onPress={onSelectLanguage}>
            <Ionicons name="language-outline" size={20} color={Colors.primaryForest} />
            <Text style={styles.menuText}>{t('changeLanguageMenu')} ({profile?.preferred_language || preferredLanguage || 'en'})</Text>
            <Ionicons name="chevron-forward-outline" size={18} color={Colors.secondaryText} />
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.menuItem}
            onPress={() =>
              Alert.alert(
                t('notificationsMenu'),
                t('comingSoonNotificationsMsg')
              )
            }
          >
            <Ionicons name="notifications-outline" size={20} color={Colors.primaryForest} />
            <Text style={styles.menuText}>{t('notificationsMenu')}</Text>
            <Ionicons name="chevron-forward-outline" size={18} color={Colors.secondaryText} />
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.menuItem}
            onPress={() =>
              Alert.alert(
                t('privacyAlertTitle'),
                t('privacyAlertMsg')
              )
            }
          >
            <Ionicons name="shield-checkmark-outline" size={20} color={Colors.primaryForest} />
            <Text style={styles.menuText}>{t('privacyMenu')}</Text>
            <Ionicons name="chevron-forward-outline" size={18} color={Colors.secondaryText} />
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.menuItem}
            onPress={() =>
              Alert.alert(
                t('helplineAlertTitle'),
                t('helplineAlertMsg')
              )
            }
          >
            <Ionicons name="help-circle-outline" size={20} color={Colors.primaryForest} />
            <Text style={styles.menuText}>{t('helplineMenu')}</Text>
            <Ionicons name="chevron-forward-outline" size={18} color={Colors.secondaryText} />
          </TouchableOpacity>
        </View>

        {/* Auth / Session Button */}
        {isAuthenticated ? (
          <TouchableOpacity style={styles.logoutBtn} onPress={logout}>
            <Ionicons name="log-out-outline" size={18} color={Colors.error} />
            <Text style={styles.logoutText}>{t('logoutBtn')}</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            style={styles.loginBtn}
            onPress={() => login('local-dev-token')}
          >
            <Ionicons name="log-in-outline" size={18} color={Colors.white} />
            <Text style={styles.loginText}>{t('loginDevBtn')}</Text>
          </TouchableOpacity>
        )}
      </ScrollView>
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
  refreshBtn: {
    padding: 6,
    borderRadius: 8,
    backgroundColor: '#F0FDF4',
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
  loadingBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#F0FDF4',
    padding: 10,
    borderRadius: 8,
    marginBottom: 12,
  },
  loadingText: { fontSize: 12, color: Colors.primaryForest },
  errorCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#FEE2E2',
    padding: 12,
    borderRadius: 8,
    marginBottom: 12,
  },
  errorText: { fontSize: 12, color: Colors.error, flex: 1 },
  profileHeaderCard: {
    backgroundColor: Colors.white,
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  avatar: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: Colors.primaryForest,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 10,
  },
  avatarText: { color: Colors.white, fontSize: 24, fontWeight: 'bold' },
  userName: { fontSize: 18, fontWeight: 'bold', color: Colors.primaryText },
  userPhone: { fontSize: 12, color: Colors.secondaryText, marginTop: 2 },
  userMeta: { fontSize: 12, color: Colors.secondaryText, marginTop: 4, textAlign: 'center' },
  verifiedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#DCFCE7',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    marginTop: 10,
    gap: 4,
  },
  verifiedText: { fontSize: 11, color: '#15803D', fontWeight: 'bold' },
  editBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 12,
    backgroundColor: '#F0FDF4',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    borderColor: Colors.secondaryLeaf,
    borderWidth: 1,
  },
  editBtnText: { fontSize: 12, color: Colors.primaryForest, fontWeight: 'bold' },
  editCard: {
    backgroundColor: Colors.white,
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#CBD5E1',
  },
  editTitle: { fontSize: 15, fontWeight: 'bold', color: Colors.primaryText, marginBottom: 12 },
  saveErrorText: { color: Colors.error, fontSize: 12, marginBottom: 8 },
  inputLabel: { fontSize: 12, fontWeight: '600', color: Colors.primaryText, marginTop: 8, marginBottom: 4 },
  input: {
    backgroundColor: Colors.softCream,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    fontSize: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  toggleChip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
    backgroundColor: '#F1F5F9',
    borderWidth: 1,
    borderColor: '#CBD5E1',
  },
  toggleChipActive: {
    backgroundColor: '#DCFCE7',
    borderColor: '#16A34A',
  },
  toggleChipText: {
    fontSize: 12,
    fontWeight: '600',
    color: Colors.secondaryText,
  },
  toggleChipTextActive: {
    color: '#15803D',
    fontWeight: 'bold',
  },
  editActions: { flexDirection: 'row', gap: 10, marginTop: 16 },
  cancelBtn: {
    flex: 1,
    backgroundColor: '#F1F5F9',
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  cancelBtnText: { color: Colors.secondaryText, fontWeight: 'bold', fontSize: 13 },
  saveBtn: {
    flex: 1,
    backgroundColor: Colors.primaryForest,
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  saveBtnText: { color: Colors.white, fontWeight: 'bold', fontSize: 13 },
  detailsCard: {
    backgroundColor: Colors.white,
    borderRadius: 14,
    padding: 14,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  detailsCardTitle: { fontSize: 13, fontWeight: 'bold', color: Colors.primaryForest, marginBottom: 8 },
  detailRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 },
  detailKey: { fontSize: 12, color: Colors.secondaryText },
  detailVal: { fontSize: 12, fontWeight: '600', color: Colors.primaryText },
  menuGroup: {
    backgroundColor: Colors.white,
    borderRadius: 14,
    paddingHorizontal: 12,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
    gap: 12,
  },
  menuText: { flex: 1, fontSize: 13, color: Colors.primaryText },
  logoutBtn: {
    flexDirection: 'row',
    backgroundColor: '#FEE2E2',
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  logoutText: { color: Colors.error, fontWeight: 'bold', fontSize: 14 },
  loginBtn: {
    flexDirection: 'row',
    backgroundColor: Colors.primaryForest,
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  loginText: { color: Colors.white, fontWeight: 'bold', fontSize: 14 },
});