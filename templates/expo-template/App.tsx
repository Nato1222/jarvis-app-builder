import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { StyleSheet, Text, View, SafeAreaView } from 'react-native';
import { {{MODULE_COMPONENT}} } from './src/modules/{{MODULE_NAME}}/{{MODULE_COMPONENT}}';

export default function App() {
  return (
    <SafeAreaView style={styles.container}>
      <StatusBar style="auto" />
      <View style={styles.header}>
        <Text style={styles.title}>{APP_NAME}</Text>
        <Text style={styles.subtitle}>Powered by Jarvis App Builder</Text>
      </View>
      <View style={styles.content}>
        <{{MODULE_COMPONENT}} />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  header: {
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginTop: 4,
  },
  content: {
    flex: 1,
    padding: 20,
  },
});
