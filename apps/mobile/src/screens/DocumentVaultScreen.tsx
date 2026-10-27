import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Image } from 'react-native';
import { Colors } from '../constants/colors';
import Ionicons from '@expo/vector-icons/Ionicons';

interface Props {
  onBack: () => void;
}

const DOCS = [
  { id: '1', title: 'पहचान पत्र (Aadhaar Card)', status: 'सत्यापित (Verified)', icon: 'card-outline', color: '#16A34A' },
  { id: '2', title: 'खसरा/खतौनी (Land Records)', status: 'अपलोड किया गया (Uploaded)', icon: 'document-text-outline', color: '#16A34A' },
  { id: '3', title: 'बैंक पासबुक (Bank Passbook)', status: 'लंबित (Action Required)', icon: 'alert-circle-outline', color: Colors.error },
  { id: '4', title: 'आय प्रमाण पत्र (Income Certificate)', status: 'नहीं जोड़ा गया (Not Added)', icon: 'cloud-upload-outline', color: Colors.secondaryText },
];

export default function DocumentVaultScreen({ onBack }: Props) {
  return (
    <View style={styles.container}>
      {/* Top Header with Back Button & Logo */}
      <View style={styles.topHeader}>
        <TouchableOpacity style={styles.backBtn} onPress={onBack}>
          <Ionicons name="arrow-back" size={24} color={Colors.primaryText} />
        </TouchableOpacity>
        <Image source={require('../../assets/logo.png')} style={styles.logo} />
        <View>
          <Text style={styles.headerTitle}>दस्तावेज़ वॉल्ट • Locker</Text>
          <Text style={styles.subTitleHeader}>सुरक्षित दस्तावेज़ प्रबंधन</Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={{ padding: 16 }}>
        <Text style={styles.sectionDesc}>
          सरकारी योजनाओं और सब्सिडी के आवेदन हेतु अपने दस्तावेज़ सुरक्षित रूप से सहेजें।
        </Text>

        {DOCS.map((doc) => (
          <View key={doc.id} style={styles.docCard}>
            <Ionicons name={doc.icon as any} size={28} color={doc.color} />
            <View style={{ flex: 1, marginLeft: 12 }}>
              <Text style={styles.docTitle}>{doc.title}</Text>
              <Text style={[styles.docStatus, { color: doc.color }]}>{doc.status}</Text>
            </View>
            <TouchableOpacity style={styles.uploadBtn}>
              <Ionicons name="camera-outline" size={20} color={Colors.primaryForest} />
            </TouchableOpacity>
          </View>
        ))}

        {/* Privacy Assurance Banner */}
        <View style={styles.privacyCard}>
          <Ionicons name="shield-checkmark-outline" size={20} color={Colors.primaryForest} />
          <Text style={styles.privacyText}>
            आपकी जानकारी 256-bit एन्क्रिप्शन के साथ पूरी तरह सुरक्षित है। दस्तावेज़ केवल आपकी सहमति से साझा किए जाते हैं।
          </Text>
        </View>
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
});