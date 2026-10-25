import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Image } from 'react-native';
import { Colors } from '../constants/colors';
import Ionicons from '@expo/vector-icons/Ionicons';

interface Props {
  onBack: () => void;
  onSelectLanguage?:()=>void;
}

export default function ProfileScreen({ onBack ,onSelectLanguage}: Props) {
  return (
    <View style={styles.container}>
      {/* Top Header with Back Button & Logo */}
      <View style={styles.topHeader}>
        <TouchableOpacity style={styles.backBtn} onPress={onBack}>
          <Ionicons name="arrow-back" size={24} color={Colors.primaryText} />
        </TouchableOpacity>
        <Image source={require('../../assets/logo.png')} style={styles.logo} />
        <View>
          <Text style={styles.headerTitle}>प्रोफाइल (Profile)</Text>
          <Text style={styles.subTitleHeader}>खाता एवं सेटिंग्स</Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={{ padding: 16 }}>
        {/* Profile Card Header */}
        <View style={styles.profileHeaderCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>र</Text>
          </View>
          <Text style={styles.userName}>रमेश कुमार</Text>
          <Text style={styles.userPhone}>+91 98765 43210</Text>
          <Text style={styles.userMeta}>सीहोर, मध्य प्रदेश • लघु कृषक</Text>

          <View style={styles.verifiedBadge}>
            <Ionicons name="checkmark-circle" size={14} color="#16A34A" />
            <Text style={styles.verifiedText}>e-KYC Verified Farmer</Text>
          </View>
        </View>

        {/* Settings Menu Options */}
        <View style={styles.menuGroup}>
          <TouchableOpacity style={styles.menuItem} onPress={onSelectLanguage}>
            <Ionicons name="language-outline" size={20} color={Colors.primaryForest} />
            <Text style={styles.menuText}>भाषा बदलें (Change Language)</Text>
            <Ionicons name="chevron-forward-outline" size={18} color={Colors.secondaryText} />
          </TouchableOpacity>

          <TouchableOpacity style={styles.menuItem}>
            <Ionicons name="notifications-outline" size={20} color={Colors.primaryForest} />
            <Text style={styles.menuText}>अधिसूचनाएं (Notifications)</Text>
            <Ionicons name="chevron-forward-outline" size={18} color={Colors.secondaryText} />
          </TouchableOpacity>

          <TouchableOpacity style={styles.menuItem}>
            <Ionicons name="shield-checkmark-outline" size={20} color={Colors.primaryForest} />
            <Text style={styles.menuText}>गोपनीयता और सहमति (Privacy)</Text>
            <Ionicons name="chevron-forward-outline" size={18} color={Colors.secondaryText} />
          </TouchableOpacity>

          <TouchableOpacity style={styles.menuItem}>
            <Ionicons name="help-circle-outline" size={20} color={Colors.primaryForest} />
            <Text style={styles.menuText}>सहायता और हेल्पलाइन (Help & Helpline)</Text>
            <Ionicons name="chevron-forward-outline" size={18} color={Colors.secondaryText} />
          </TouchableOpacity>
        </View>

        {/* Logout Button */}
        <TouchableOpacity style={styles.logoutBtn}>
          <Ionicons name="log-out-outline" size={18} color={Colors.error} />
          <Text style={styles.logoutText}>लॉग आउट (Logout)</Text>
        </TouchableOpacity>
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
  profileHeaderCard: {
    backgroundColor: Colors.white,
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
    marginBottom: 20,
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
  userPhone: { fontSize: 13, color: Colors.secondaryText, marginTop: 2 },
  userMeta: { fontSize: 12, color: Colors.secondaryText, marginTop: 4 },
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
  menuText: { flex: 1, fontSize: 14, color: Colors.primaryText },
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
});