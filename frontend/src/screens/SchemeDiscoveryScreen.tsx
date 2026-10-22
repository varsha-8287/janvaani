// import React, { useState } from 'react';
// import { View, Text, StyleSheet, FlatList, TextInput, TouchableOpacity } from 'react-native';
// import { Colors } from '../constants/colors';
// import Ionicons from '@expo/vector-icons/Ionicons';

// const MOCK_SCHEMES = [
//   {
//     id: '1',
//     title: 'PM-किसान सम्मान निधि',
//     englishTitle: 'PM-KISAN Samman Nidhi',
//     authority: 'कृषि एवं किसान कल्याण मंत्रालय',
//     benefit: '₹6,000 / वर्ष',
//     desc: 'सभी पात्र भू-धारक किसान परिवारों को प्रति वर्ष ₹6,000 की आय सहायता।',
//     verified: true,
//   },
//   {
//     id: '2',
//     title: 'प्रधानमंत्री फसल बीमा योजना',
//     englishTitle: 'PM Fasal Bima Yojana',
//     authority: 'कृषि मंत्रालय',
//     benefit: 'फसल सुरक्षा कवच',
//     desc: 'प्राकृतिक आपदाओं, कीटों व रोगों से सुरक्षा हेतु न्यूनतम प्रीमियम पर बीमा।',
//     verified: true,
//   },
//   {
//     id: '3',
//     title: 'किसान क्रेडिट कार्ड (KCC)',
//     englishTitle: 'Kisan Credit Card',
//     authority: 'नाबार्ड एवं सहकारी बैंक',
//     benefit: '4% प्रभावी ब्याज',
//     desc: 'समय पर पुनर्भुगतान पर 3 लाख रुपये तक का किफ़ायती रियायती ऋण।',
//     verified: true,
//   },
// ];

// export default function SchemeDiscoveryScreen() {
//   const [query, setQuery] = useState('');

//   return (
//     <View style={styles.container}>
//       {/* Search Header */}
//       <View style={styles.searchContainer}>
//         <Ionicons name="search-outline" size={20} color={Colors.secondaryText} />
//         <TextInput
//           style={styles.searchInput}
//           placeholder="योजनाएं खोजें (Search Schemes)..."
//           value={query}
//           onChangeText={setQuery}
//         />
//       </View>

//       <FlatList
//         data={MOCK_SCHEMES}
//         keyExtractor={(item) => item.id}
//         renderItem={({ item }) => (
//           <View style={styles.card}>
//             <View style={styles.cardHeader}>
//               <Text style={styles.authority}>{item.authority}</Text>
//               {item.verified && (
//                 <View style={styles.badge}>
//                   <Text style={styles.badgeText}>✓ Verified Source</Text>
//                 </View>
//               )}
//             </View>
//             <Text style={styles.title}>{item.title}</Text>
//             <Text style={styles.englishTitle}>{item.englishTitle}</Text>
//             <Text style={styles.desc}>{item.desc}</Text>
//             <View style={styles.cardFooter}>
//               <Text style={styles.benefit}>{item.benefit}</Text>
//               <TouchableOpacity style={styles.actionBtn}>
//                 <Text style={styles.actionBtnText}>पात्रता जांचें ›</Text>
//               </TouchableOpacity>
//             </View>
//           </View>
//         )}
//       />
//     </View>
//   );
// }

// const styles = StyleSheet.create({
//   container: { flex: 1, backgroundColor: Colors.softCream, padding: 16 },
//   searchContainer: {
//     flexDirection: 'row',
//     alignItems: 'center',
//     backgroundColor: Colors.white,
//     paddingHorizontal: 12,
//     borderRadius: 12,
//     height: 48,
//     marginBottom: 16,
//   },
//   searchInput: { flex: 1, marginLeft: 8, fontSize: 14 },
//   card: {
//     backgroundColor: Colors.white,
//     borderRadius: 16,
//     padding: 16,
//     marginBottom: 12,
//     borderWidth: 1,
//     borderColor: '#E2E8F0',
//   },
//   cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
//   authority: { fontSize: 11, color: Colors.secondaryText },
//   badge: { backgroundColor: '#DCFCE7', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6 },
//   badgeText: { fontSize: 10, color: Colors.primaryForest, fontWeight: 'bold' },
//   title: { fontSize: 16, fontWeight: 'bold', color: Colors.primaryText, marginTop: 4 },
//   englishTitle: { fontSize: 12, color: Colors.secondaryText, marginBottom: 8 },
//   desc: { fontSize: 13, color: Colors.primaryText, lineHeight: 18, marginBottom: 12 },
//   cardFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
//   benefit: { fontSize: 15, fontWeight: 'bold', color: Colors.primaryForest },
//   actionBtn: { backgroundColor: Colors.primaryForest, paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8 },
//   actionBtnText: { color: Colors.white, fontWeight: 'bold', fontSize: 12 },
// });

import React, { useState } from 'react';
import { View, Text, StyleSheet, FlatList, TextInput, TouchableOpacity, Image } from 'react-native';
import { Colors } from '../constants/colors';
import Ionicons from '@expo/vector-icons/Ionicons';

interface Props {
  onBack: () => void;
}

const MOCK_SCHEMES = [
  {
    id: '1',
    title: 'PM-किसान सम्मान निधि',
    englishTitle: 'PM-KISAN Samman Nidhi',
    authority: 'कृषि एवं किसान कल्याण मंत्रालय',
    benefit: '₹6,000 / वर्ष',
    desc: 'सभी पात्र भू-धारक किसान परिवारों को प्रति वर्ष ₹6,000 की आय सहायता।',
    verified: true,
  },
  {
    id: '2',
    title: 'प्रधानमंत्री फसल बीमा योजना',
    englishTitle: 'PM Fasal Bima Yojana',
    authority: 'कृषि मंत्रालय',
    benefit: 'फसल सुरक्षा कवच',
    desc: 'प्राकृतिक आपदाओं, कीटों व रोगों से सुरक्षा हेतु न्यूनतम प्रीमियम पर बीमा।',
    verified: true,
  },
  {
    id: '3',
    title: 'किसान क्रेडिट कार्ड (KCC)',
    englishTitle: 'Kisan Credit Card',
    authority: 'नाबार्ड एवं सहकारी बैंक',
    benefit: '4% प्रभावी ब्याज',
    desc: 'समय पर पुनर्भुगतान पर 3 लाख रुपये तक का किफ़ायती रियायती ऋण।',
    verified: true,
  },
];

export default function SchemeDiscoveryScreen({ onBack }: Props) {
  const [query, setQuery] = useState('');

  // Filter schemes dynamically based on user input
  const filteredSchemes = MOCK_SCHEMES.filter(
    (scheme) =>
      scheme.title.toLowerCase().includes(query.toLowerCase()) ||
      scheme.englishTitle.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <View style={styles.container}>
      {/* Top Bar Header with Back Button & Logo */}
      <View style={styles.topHeader}>
        <TouchableOpacity style={styles.backBtn} onPress={onBack}>
          <Ionicons name="arrow-back" size={24} color={Colors.primaryText} />
        </TouchableOpacity>
        <Image source={require('../../assets/logo.png')} style={styles.logo} />
        <Text style={styles.headerTitle}>योजनाएं (Schemes)</Text>
      </View>

      {/* Search Header */}
      <View style={styles.searchContainer}>
        <Ionicons name="search-outline" size={20} color={Colors.secondaryText} />
        <TextInput
          style={styles.searchInput}
          placeholder="योजनाएं खोजें (Search Schemes)..."
          value={query}
          onChangeText={setQuery}
        />
        {query.length > 0 && (
          <TouchableOpacity onPress={() => setQuery('')}>
            <Ionicons name="close-circle" size={18} color={Colors.secondaryText} />
          </TouchableOpacity>
        )}
      </View>

      {/* Scheme List */}
      <FlatList
        data={filteredSchemes}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <Text style={styles.authority}>{item.authority}</Text>
              {item.verified && (
                <View style={styles.badge}>
                  <Text style={styles.badgeText}>✓ Verified Source</Text>
                </View>
              )}
            </View>
            <Text style={styles.title}>{item.title}</Text>
            <Text style={styles.englishTitle}>{item.englishTitle}</Text>
            <Text style={styles.desc}>{item.desc}</Text>
            <View style={styles.cardFooter}>
              <Text style={styles.benefit}>{item.benefit}</Text>
              <TouchableOpacity style={styles.actionBtn}>
                <Text style={styles.actionBtnText}>पात्रता जांचें ›</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>कोई योजना नहीं मिली (No schemes found)</Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.softCream, padding: 16 },
  topHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    gap: 12,
  },
  backBtn: {
    padding: 6,
    borderRadius: 8,
    backgroundColor: Colors.white,
    elevation: 2,
  },
  logo: {
    width: 32,
    height: 32,
    resizeMode: 'contain',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: Colors.primaryText,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.white,
    paddingHorizontal: 12,
    borderRadius: 12,
    height: 48,
    marginBottom: 16,
  },
  searchInput: { flex: 1, marginLeft: 8, fontSize: 14 },
  card: {
    backgroundColor: Colors.white,
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  authority: { fontSize: 11, color: Colors.secondaryText },
  badge: { backgroundColor: '#DCFCE7', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6 },
  badgeText: { fontSize: 10, color: Colors.primaryForest, fontWeight: 'bold' },
  title: { fontSize: 16, fontWeight: 'bold', color: Colors.primaryText, marginTop: 4 },
  englishTitle: { fontSize: 12, color: Colors.secondaryText, marginBottom: 8 },
  desc: { fontSize: 13, color: Colors.primaryText, lineHeight: 18, marginBottom: 12 },
  cardFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  benefit: { fontSize: 15, fontWeight: 'bold', color: Colors.primaryForest },
  actionBtn: { backgroundColor: Colors.primaryForest, paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8 },
  actionBtnText: { color: Colors.white, fontWeight: 'bold', fontSize: 12 },
  emptyContainer: { alignItems: 'center', marginTop: 32 },
  emptyText: { fontSize: 14, color: Colors.secondaryText },
});