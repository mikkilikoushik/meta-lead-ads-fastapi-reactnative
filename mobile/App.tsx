import React from "react";
import { FlatList, SafeAreaView, StatusBar, StyleSheet, Text, View } from "react-native";

import { API_URL } from "./src/config";
import { Lead } from "./src/types";
import { useLeads } from "./src/useLeads";

const STATUS_COLOR = { live: "#16a34a", connecting: "#f59e0b", offline: "#dc2626" } as const;

function formatTime(iso: string): string {
  const d = new Date(iso);
  return isNaN(d.getTime()) ? iso : d.toLocaleString();
}

function LeadCard({ lead }: { lead: Lead }) {
  return (
    <View style={styles.card}>
      <Text style={styles.name}>{lead.name ?? "—"}</Text>
      <Text style={styles.line}>✉️  {lead.email ?? "—"}</Text>
      <Text style={styles.line}>📞  {lead.phone ?? "—"}</Text>
      <Text style={styles.time}>{formatTime(lead.created_time)}</Text>
    </View>
  );
}

export default function App() {
  const { leads, status, error } = useLeads();

  if (!API_URL) {
    return (
      <SafeAreaView style={styles.center}>
        <Text style={styles.name}>EXPO_PUBLIC_API_URL is not set</Text>
        <Text style={styles.line}>Copy mobile/.env.example to mobile/.env and restart Expo.</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />
      <View style={styles.header}>
        <Text style={styles.title}>Leads ({leads.length})</Text>
        <View style={styles.badge}>
          <View style={[styles.dot, { backgroundColor: STATUS_COLOR[status] }]} />
          <Text style={styles.badgeText}>{status}</Text>
        </View>
      </View>
      {error && <Text style={styles.error}>{error}</Text>}
      <FlatList
        data={leads}
        keyExtractor={(l) => String(l.id)}
        renderItem={({ item }) => <LeadCard lead={item} />}
        contentContainerStyle={leads.length === 0 ? styles.emptyWrap : styles.list}
        ListEmptyComponent={<Text style={styles.line}>Waiting for leads…</Text>}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f3f4f6", paddingTop: StatusBar.currentHeight ?? 0 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24 },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", padding: 16 },
  title: { fontSize: 22, fontWeight: "700" },
  badge: { flexDirection: "row", alignItems: "center", gap: 6 },
  dot: { width: 10, height: 10, borderRadius: 5 },
  badgeText: { fontSize: 13, color: "#374151", textTransform: "capitalize" },
  error: { color: "#dc2626", paddingHorizontal: 16, paddingBottom: 8 },
  list: { padding: 16, gap: 12 },
  emptyWrap: { flexGrow: 1, alignItems: "center", justifyContent: "center" },
  card: { backgroundColor: "#fff", borderRadius: 12, padding: 16, gap: 4, elevation: 2, shadowColor: "#000", shadowOpacity: 0.08, shadowRadius: 6, shadowOffset: { width: 0, height: 2 } },
  name: { fontSize: 17, fontWeight: "600" },
  line: { fontSize: 15, color: "#4b5563" },
  time: { fontSize: 12, color: "#9ca3af", marginTop: 4 },
});
