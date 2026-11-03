import React, { useState } from 'react';
import { StatusBar, StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from '@expo/vector-icons/Ionicons';

import HomeScreen from './src/screens/HomeScreen';
import SchemeDiscoveryScreen from './src/screens/SchemeDiscoveryScreen';
import AIChatScreen from './src/screens/AIChatScreen';
import DocumentVaultScreen from './src/screens/DocumentVaultScreen';
import ProfileScreen from './src/screens/ProfileScreen';
import LanguageSelectScreen from './src/screens/LanguageSelectScreen';
import { Colors } from './src/constants/colors';
import { AuthProvider, useTranslation } from './src/context/AuthContext';

type ScreenType = 'home' | 'schemes' | 'chat' | 'docs' | 'profile' | 'language';

function MainApp() {
  const [currentScreen, setCurrentScreen] = useState<ScreenType>('home');
  const { t } = useTranslation();

  const goHome = () => setCurrentScreen('home');

  return (
    <SafeAreaView style={styles.container} edges={['top', 'left', 'right']}>
      <StatusBar barStyle="dark-content" backgroundColor={Colors.softCream} />

      {/* Active Screen Display */}
      <View style={styles.content}>
        {currentScreen === 'home' && (
          <HomeScreen
            onNavigate={(screen) => setCurrentScreen(screen as ScreenType)}
            onSelectLanguage={() => setCurrentScreen('language')}
          />
        )}
        {currentScreen === 'schemes' && <SchemeDiscoveryScreen onBack={goHome} />}
        {currentScreen === 'chat' && <AIChatScreen onBack={goHome} />}
        {currentScreen === 'docs' && <DocumentVaultScreen onBack={goHome} />}
        {currentScreen === 'profile' && (
          <ProfileScreen
            onBack={goHome}
            onSelectLanguage={() => setCurrentScreen('language')}
          />
        )}
        {currentScreen === 'language' && (
          <LanguageSelectScreen onContinue={goHome} />
        )}
      </View>

      {/* Bottom Navigation Tab Bar (Hidden when on Language Screen) */}
      {currentScreen !== 'language' && (
        <View style={styles.bottomBar}>
          <TouchableOpacity style={styles.tabItem} onPress={() => setCurrentScreen('home')}>
            <Ionicons
              name={currentScreen === 'home' ? 'home' : 'home-outline'}
              size={22}
              color={currentScreen === 'home' ? Colors.primaryForest : Colors.secondaryText}
            />
            <Text style={[styles.tabLabel, currentScreen === 'home' && styles.activeTabLabel]}>{t('tabHome')}</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.tabItem} onPress={() => setCurrentScreen('schemes')}>
            <Ionicons
              name={currentScreen === 'schemes' ? 'search' : 'search-outline'}
              size={22}
              color={currentScreen === 'schemes' ? Colors.primaryForest : Colors.secondaryText}
            />
            <Text style={[styles.tabLabel, currentScreen === 'schemes' && styles.activeTabLabel]}>{t('tabSchemes')}</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.tabItem} onPress={() => setCurrentScreen('chat')}>
            <View style={styles.aiTabBadge}>
              <Ionicons name="mic" size={20} color="#78350F" />
            </View>
            <Text style={[styles.tabLabel, currentScreen === 'chat' && styles.activeTabLabel]}>{t('tabAskAi')}</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.tabItem} onPress={() => setCurrentScreen('docs')}>
            <Ionicons
              name={currentScreen === 'docs' ? 'folder' : 'folder-outline'}
              size={22}
              color={currentScreen === 'docs' ? Colors.primaryForest : Colors.secondaryText}
            />
            <Text style={[styles.tabLabel, currentScreen === 'docs' && styles.activeTabLabel]}>{t('tabVault')}</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.tabItem} onPress={() => setCurrentScreen('profile')}>
            <Ionicons
              name={currentScreen === 'profile' ? 'person' : 'person-outline'}
              size={22}
              color={currentScreen === 'profile' ? Colors.primaryForest : Colors.secondaryText}
            />
            <Text style={[styles.tabLabel, currentScreen === 'profile' && styles.activeTabLabel]}>{t('tabProfile')}</Text>
          </TouchableOpacity>
        </View>
      )}
    </SafeAreaView>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <MainApp />
      </AuthProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.softCream,
  },
  content: {
    flex: 1,
  },
  bottomBar: {
    flexDirection: 'row',
    height: 64,
    backgroundColor: Colors.white,
    borderTopWidth: 1,
    borderTopColor: '#E2E8F0',
    alignItems: 'center',
    justifyContent: 'space-around',
    paddingBottom: 4,
  },
  tabItem: {
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
  },
  tabLabel: {
    fontSize: 10,
    color: Colors.secondaryText,
    marginTop: 2,
  },
  activeTabLabel: {
    color: Colors.primaryForest,
    fontWeight: 'bold',
  },
  aiTabBadge: {
    backgroundColor: Colors.warmGolden,
    padding: 6,
    borderRadius: 16,
    marginTop: -10,
  },
});
