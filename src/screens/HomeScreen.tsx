import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Image } from 'react-native';
import { Colors } from '../constants/colors';
import Ionicons from '@expo/vector-icons/Ionicons';

export default function HomeScreen({ onNavigate,onSelectLanguage }: { onNavigate: (screen: string) => void ;onSelectLanguage?:()=>void;}) {
  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      {/* Top Bar Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.brandTitle}>Janvaani | जनवाणी</Text>
          <Text style={styles.brandSub}>आपकी आवाज, आपका अधिकार</Text>
        </View>
        <View style={styles.headerRight}>
            <TouchableOpacity style={styles.langPill} onPress={onSelectLanguage}>
                <Text style={styles.langText}>हिंदी / A</Text>
            </TouchableOpacity>
          {/* <TouchableOpacity style={styles.langPill}>
            <Text style={styles.langText}>हिंदी / A</Text>
          </TouchableOpacity> */}
          <TouchableOpacity style={styles.iconBtn}>
            <Ionicons name="notifications-outline" size={20} color={Colors.primaryText} />
          </TouchableOpacity>
        </View>
      </View>

      {/* Greeting Banner */}
      <View style={styles.userBanner}>
        <Text style={styles.greetingText}>नमस्ते, रमेश जी! 🙏</Text>
        <Text style={styles.locationText}>📍 सीहोर, मध्य प्रदेश • लघु कृषक (Small Farmer)</Text>
      </View>

      {/* Weather & Rabi Advisory Card */}
      <View style={styles.advisoryCard}>
        <View style={styles.advisoryHeader}>
          <Ionicons name="sunny-outline" size={22} color="#15803D" />
          <Text style={styles.advisoryTag}>रबी मौसम परामर्श • RABI ADVISORY</Text>
          <Text style={styles.tempText}>24°C धूप</Text>
        </View>
        <Text style={styles.advisoryTitle}>गेहूं की बुआई का उत्तम समय सक्रिय है</Text>
        <View style={styles.advisoryChips}>
          <Text style={styles.chipText}>👍 मृदा नमी: पर्याप्त (Adequate)</Text>
          <Text style={styles.chipText}>⚙️ डीएपी स्टॉक उपलब्ध</Text>
        </View>
      </View>

      {/* Janvaani AI Voice Search Banner */}
      <View style={styles.aiCard}>
        <View style={styles.aiBadge}>
          <Text style={styles.aiBadgeText}>JANVAANI AI • आपका डिजिटल साथी</Text>
        </View>
        <Text style={styles.aiHeading}>अपनी भाषा में बोलें, सही योजना तुरंत पाएं</Text>
        <Text style={styles.aiSub}>खाद सब्सिडी, फसल बीमा, केसीसी लोन या ज़मीन के दस्तावेज़ के बारे में बेझिझक पूछें।</Text>
        
        <View style={styles.aiButtons}>
          <TouchableOpacity style={styles.voiceBtn} onPress={() => onNavigate('chat')}>
            <Ionicons name="mic" size={18} color="#78350F" />
            <Text style={styles.voiceBtnText}>बोलकर पूछें</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.typeBtn} onPress={() => onNavigate('chat')}>
            <Ionicons name="chatbox-ellipses-outline" size={18} color={Colors.white} />
            <Text style={styles.typeBtnText}>लिखकर पूछें</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Key Services 2x3 Grid */}
      <Text style={styles.sectionTitle}>मुख्य सेवाएं • Key Services</Text>
      <View style={styles.grid}>
        <TouchableOpacity style={styles.gridCard} onPress={() => onNavigate('schemes')}>
          <Ionicons name="search-outline" size={24} color={Colors.primaryForest} />
          <Text style={styles.gridTitle}>योजनाएं खोजें</Text>
          <Text style={styles.gridSub}>Discover Schemes</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.gridCard} onPress={() => onNavigate('chat')}>
          <Ionicons name="checkmark-done-circle-outline" size={24} color={Colors.primaryForest} />
          <Text style={styles.gridTitle}>पात्रता जांचें</Text>
          <Text style={styles.gridSub}>Check Eligibility</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.gridCard} onPress={() => onNavigate('docs')}>
          <Ionicons name="folder-open-outline" size={24} color={Colors.primaryForest} />
          <Text style={styles.gridTitle}>दस्तावेज़ वॉल्ट</Text>
          <Text style={styles.gridSub}>Digital Locker</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.gridCard} onPress={() => onNavigate('docs')}>
          <Ionicons name="time-outline" size={24} color={Colors.primaryForest} />
          <Text style={styles.gridTitle}>आवेदन स्थिति</Text>
          <Text style={styles.gridSub}>My Applications</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.gridCard}>
          <Ionicons name="alert-circle-outline" size={24} color={Colors.primaryForest} />
          <Text style={styles.gridTitle}>शिकायत निवारण</Text>
          <Text style={styles.gridSub}>Grievance Portal</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.gridCard}>
          <Ionicons name="business-outline" size={24} color={Colors.primaryForest} />
          <Text style={styles.gridTitle}>पैक्स सहकारी</Text>
          <Text style={styles.gridSub}>PACS & Societies</Text>
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
  userBanner: { marginBottom: 16 },
  greetingText: { fontSize: 20, fontWeight: 'bold', color: Colors.primaryText },
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
});