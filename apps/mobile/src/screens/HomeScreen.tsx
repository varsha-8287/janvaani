import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert } from 'react-native';
import { Colors } from '../constants/colors';
import Ionicons from '@expo/vector-icons/Ionicons';
import { useAuth } from '../context/AuthContext';

interface Props {
  onNavigate: (screen: string) => void;
  onSelectLanguage?: () => void;
}

export default function HomeScreen({ onNavigate, onSelectLanguage }: Props) {
  const { profile, preferredLanguage, t } = useAuth();

  const citizenName = profile?.attributes?.name || t('greetingCitizen');
  const citizenLocation = [profile?.district, profile?.state].filter(Boolean).join(', ') || t('locationNotSet');
  const citizenCategory = profile?.attributes?.farmer_category || t('farmerCategoryNotSet');

  const handleUnsupportedFeature = (title: string, message: string) => {
    Alert.alert(title, message);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      {/* Top Bar Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.brandTitle}>{t('brandTitle')}</Text>
          <Text style={styles.brandSub}>{t('brandSub')}</Text>
        </View>
        <View style={styles.headerRight}>
          <TouchableOpacity style={styles.langPill} onPress={onSelectLanguage}>
            <Text style={styles.langText}>
              {preferredLanguage?.toUpperCase() || 'EN'} / A
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.iconBtn}
            onPress={() =>
              handleUnsupportedFeature(
                t('notificationsMenu'),
                t('comingSoonNotificationsMsg')
              )
            }
          >
            <Ionicons name="notifications-outline" size={20} color={Colors.primaryText} />
          </TouchableOpacity>
        </View>
      </View>

      {/* Greeting Banner */}
      <TouchableOpacity style={styles.userBanner} onPress={() => onNavigate('profile')}>
        <View style={{ flex: 1 }}>
          <Text style={styles.greetingText}>{t('greetingGreeting')}, {citizenName}! 🙏</Text>
          <Text style={styles.locationText}>
            📍 {citizenLocation} • {citizenCategory}
          </Text>
        </View>
        <Ionicons name="chevron-forward" size={18} color={Colors.secondaryText} />
      </TouchableOpacity>

      {/* Advisory Card */}
      <View style={styles.advisoryCard}>
        <View style={styles.advisoryHeader}>
          <Ionicons name="sunny-outline" size={22} color="#15803D" />
          <Text style={styles.advisoryTag}>{t('seasonalAdvisoryTag')}</Text>
          <Text style={styles.tempText}>{t('seasonalAdvisoryTemp')}</Text>
        </View>
        <Text style={styles.advisoryTitle}>{t('seasonalAdvisoryTitle')}</Text>
        <View style={styles.advisoryChips}>
          <Text style={styles.chipText}>{t('seasonalChip1')}</Text>
          <Text style={styles.chipText}>{t('seasonalChip2')}</Text>
        </View>
      </View>

      {/* Janvaani AI Voice Search Banner */}
      <View style={styles.aiCard}>
        <View style={styles.aiBadge}>
          <Text style={styles.aiBadgeText}>{t('aiCardBadge')}</Text>
        </View>
        <Text style={styles.aiHeading}>{t('aiCardHeading')}</Text>
        <Text style={styles.aiSub}>
          {t('aiCardSub')}
        </Text>

        <View style={styles.aiButtons}>
          <TouchableOpacity style={styles.voiceBtn} onPress={() => onNavigate('chat')}>
            <Ionicons name="mic" size={18} color="#78350F" />
            <Text style={styles.voiceBtnText}>{t('askByVoice')}</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.typeBtn} onPress={() => onNavigate('chat')}>
            <Ionicons name="chatbox-ellipses-outline" size={18} color={Colors.white} />
            <Text style={styles.typeBtnText}>{t('askByTyping')}</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Key Services 2x3 Grid */}
      <Text style={styles.sectionTitle}>{t('keyServicesTitle')}</Text>
      <View style={styles.grid}>
        <TouchableOpacity style={styles.gridCard} onPress={() => onNavigate('schemes')}>
          <Ionicons name="search-outline" size={24} color={Colors.primaryForest} />
          <Text style={styles.gridTitle}>{t('serviceDiscoverSchemes')}</Text>
          <Text style={styles.gridSub}>{t('serviceDiscoverSchemesSub')}</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.gridCard} onPress={() => onNavigate('schemes')}>
          <Ionicons name="checkmark-done-circle-outline" size={24} color={Colors.primaryForest} />
          <Text style={styles.gridTitle}>{t('serviceCheckEligibility')}</Text>
          <Text style={styles.gridSub}>{t('serviceCheckEligibilitySub')}</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.gridCard} onPress={() => onNavigate('docs')}>
          <Ionicons name="folder-open-outline" size={24} color={Colors.primaryForest} />
          <Text style={styles.gridTitle}>{t('serviceDigitalLocker')}</Text>
          <Text style={styles.gridSub}>{t('serviceDigitalLockerSub')}</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.gridCard} onPress={() => onNavigate('docs')}>
          <Ionicons name="time-outline" size={24} color={Colors.primaryForest} />
          <Text style={styles.gridTitle}>{t('serviceAppReadiness')}</Text>
          <Text style={styles.gridSub}>{t('serviceAppReadinessSub')}</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.gridCard, styles.disabledCard]}
          onPress={() =>
            handleUnsupportedFeature(
              t('serviceGrievance'),
              t('comingSoonGrievanceMsg')
            )
          }
        >
          <View style={styles.badgeRow}>
            <Ionicons name="alert-circle-outline" size={24} color={Colors.secondaryText} />
            <Text style={styles.comingSoonBadge}>{t('comingSoon')}</Text>
          </View>
          <Text style={styles.disabledTitle}>{t('serviceGrievance')}</Text>
          <Text style={styles.gridSub}>{t('serviceGrievanceSub')}</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.gridCard, styles.disabledCard]}
          onPress={() =>
            handleUnsupportedFeature(
              t('servicePacs'),
              t('comingSoonPacsMsg')
            )
          }
        >
          <View style={styles.badgeRow}>
            <Ionicons name="business-outline" size={24} color={Colors.secondaryText} />
            <Text style={styles.comingSoonBadge}>{t('comingSoon')}</Text>
          </View>
          <Text style={styles.disabledTitle}>{t('servicePacs')}</Text>
          <Text style={styles.gridSub}>{t('servicePacsSub')}</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.softCream },
  contentContainer: { padding: 16, paddingBottom: 80 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  brandTitle: { fontSize: 18, fontWeight: 'bold', color: Colors.primaryForest },
  brandSub: { fontSize: 11, color: Colors.secondaryText },
  headerRight: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  langPill: { backgroundColor: '#E2E8F0', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  langText: { fontSize: 12, fontWeight: 'bold', color: Colors.primaryText },
  iconBtn: { padding: 6 },
  userBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    backgroundColor: Colors.white,
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  greetingText: { fontSize: 17, fontWeight: 'bold', color: Colors.primaryText },
  locationText: { fontSize: 12, color: Colors.secondaryText, marginTop: 2 },
  advisoryCard: { backgroundColor: '#F0FDF4', borderRadius: 16, padding: 14, marginBottom: 16, borderWidth: 1, borderColor: '#DCFCE7' },
  advisoryHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6 },
  advisoryTag: { fontSize: 11, fontWeight: 'bold', color: '#15803D', flex: 1 },
  tempText: { fontSize: 11, color: Colors.secondaryText },
  advisoryTitle: { fontSize: 14, fontWeight: 'bold', color: Colors.primaryText, marginBottom: 6 },
  advisoryChips: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  chipText: { fontSize: 11, color: Colors.secondaryText },
  aiCard: { backgroundColor: Colors.primaryForest, borderRadius: 16, padding: 16, marginBottom: 20 },
  aiBadge: { backgroundColor: 'rgba(255,255,255,0.15)', alignSelf: 'flex-start', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8, marginBottom: 8 },
  aiBadgeText: { color: Colors.white, fontSize: 10, fontWeight: 'bold' },
  aiHeading: { color: Colors.white, fontSize: 17, fontWeight: 'bold', marginBottom: 6 },
  aiSub: { color: '#D1FAE5', fontSize: 12, marginBottom: 14, lineHeight: 16 },
  aiButtons: { flexDirection: 'row', gap: 10 },
  voiceBtn: { backgroundColor: Colors.warmGolden, flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 10, borderRadius: 10, gap: 6 },
  voiceBtnText: { color: '#78350F', fontWeight: 'bold', fontSize: 13 },
  typeBtn: { backgroundColor: 'rgba(255,255,255,0.2)', flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 10, borderRadius: 10, gap: 6 },
  typeBtnText: { color: Colors.white, fontWeight: 'bold', fontSize: 13 },
  sectionTitle: { fontSize: 16, fontWeight: 'bold', color: Colors.primaryText, marginBottom: 12 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  gridCard: { width: '48%', backgroundColor: Colors.white, padding: 14, borderRadius: 14, borderBottomWidth: 2, borderBottomColor: Colors.secondaryLeaf },
  gridTitle: { fontSize: 14, fontWeight: 'bold', color: Colors.primaryText, marginTop: 8 },
  gridSub: { fontSize: 11, color: Colors.secondaryText },
  disabledCard: {
    backgroundColor: '#F8FAFC',
    borderBottomColor: '#CBD5E1',
    opacity: 0.85,
  },
  disabledTitle: { fontSize: 14, fontWeight: 'bold', color: Colors.secondaryText, marginTop: 8 },
  badgeRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  comingSoonBadge: {
    fontSize: 9,
    backgroundColor: '#E2E8F0',
    color: Colors.secondaryText,
    paddingHorizontal: 5,
    paddingVertical: 2,
    borderRadius: 4,
    fontWeight: 'bold',
  },
});