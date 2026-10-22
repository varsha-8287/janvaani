import React, { useState } from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity, TextInput } from 'react-native';
import { Colors } from '../constants/colors';
import Ionicons from '@expo/vector-icons/Ionicons';

const LANGUAGES = [
  { id: 'en', name: 'English', script: 'English' },
  { id: 'hi', name: 'हिंदी', script: 'Hindi' },
  { id: 'ta', name: 'தமிழ்', script: 'Tamil' },
  { id: 'te', name: 'తెలుగు', script: 'Telugu' },
  { id: 'kn', name: 'கன்னட / ಕನ್ನಡ', script: 'Kannada' },
  { id: 'ml', name: 'മലയാളം', script: 'Malayalam' },
  { id: 'bn', name: 'বাংলা', script: 'Bengali' },
  { id: 'gu', name: 'ગુજરાતી', script: 'Gujarati' },
  { id: 'mr', name: 'मराठी', script: 'Marathi' },
  { id: 'or', name: 'ଓଡ଼ିଆ', script: 'Odia' },
  { id: 'pa', name: 'ਪੰਜਾਬੀ', script: 'Punjabi' },
  { id: 'as', name: 'অসমীয়া', script: 'Assamese' },
];

export default function LanguageSelectScreen({ onContinue }: { onContinue: () => void }) {
  const [selected, setSelected] = useState('hi');
  const [search, setSearch] = useState('');

  const filtered = LANGUAGES.filter(
    (l) => l.name.toLowerCase().includes(search.toLowerCase()) || l.script.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Choose your language</Text>
      <Text style={styles.subtitle}>अपनी भाषा का चयन करें</Text>

      <View style={styles.searchBar}>
        <Ionicons name="search-outline" size={20} color={Colors.secondaryText} />
        <TextInput
          style={styles.searchInput}
          placeholder="Search language..."
          value={search}
          onChangeText={setSearch}
        />
      </View>

      <FlatList
        data={filtered}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => {
          const isSelected = selected === item.id;
          return (
            <TouchableOpacity
              style={[styles.row, isSelected && styles.rowSelected]}
              onPress={() => setSelected(item.id)}
            >
              <View>
                <Text style={[styles.langNative, isSelected && styles.textSelected]}>{item.name}</Text>
                <Text style={styles.langSub}>{item.script}</Text>
              </View>
              {isSelected && <Ionicons name="checkmark-circle" size={24} color={Colors.primaryForest} />}
            </TouchableOpacity>
          );
        }}
      />

      <TouchableOpacity style={styles.continueBtn} onPress={onContinue}>
        <Text style={styles.continueBtnText}>Continue • आगे बढ़ें</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.softCream, padding: 20 },
  title: { fontSize: 22, fontWeight: 'bold', color: Colors.primaryText },
  subtitle: { fontSize: 14, color: Colors.secondaryText, marginBottom: 16 },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.white,
    paddingHorizontal: 12,
    borderRadius: 12,
    marginBottom: 16,
    height: 48,
  },
  searchInput: { flex: 1, marginLeft: 8, fontSize: 15 },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: Colors.white,
    padding: 16,
    borderRadius: 12,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  rowSelected: { borderColor: Colors.primaryForest, backgroundColor: '#F0FDF4' },
  langNative: { fontSize: 18, fontWeight: 'bold', color: Colors.primaryText },
  textSelected: { color: Colors.primaryForest },
  langSub: { fontSize: 12, color: Colors.secondaryText },
  continueBtn: {
    backgroundColor: Colors.primaryForest,
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 10,
  },
  continueBtnText: { color: Colors.white, fontWeight: 'bold', fontSize: 16 },
});