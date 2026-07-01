import React, { useState, useCallback } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, RefreshControl, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../context/AuthContext';
import { disposalAPI } from '../services/api';
import { useFocusEffect } from '@react-navigation/native';

const POINTS_PER_DISPOSAL = 50;
const MIN_REDEEM = 100;
const RATE = 5;

export default function DashboardScreen({ navigation }) {
  const { user, balance, refreshBalance } = useAuth();
  const [stats, setStats] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const res = await disposalAPI.getStats();
      setStats(res.data);
    } catch {}
    await refreshBalance();
    setLoading(false);
  };

  useFocusEffect(useCallback(() => { loadData(); }, []));

  const onRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  if (loading) return <View style={styles.center}><ActivityIndicator size="large" color="#2E7D32" /></View>;

  const currentPoints = balance?.currentPoints ?? 0;
  const progressToRedeem = Math.min((currentPoints / MIN_REDEEM) * 100, 100);
  const disposalsToRedeem = Math.max(0, Math.ceil((MIN_REDEEM - currentPoints) / POINTS_PER_DISPOSAL));

  const cards = [
    { icon: 'leaf', color: '#2E7D32', label: 'Current Points', value: currentPoints.toLocaleString() },
    { icon: 'cash', color: '#F57F17', label: 'Airtime Value', value: `UGX ${(currentPoints * RATE).toLocaleString()}` },
    { icon: 'trash-bin', color: '#1565C0', label: 'Items Recycled', value: (stats?.acceptedItems ?? 0).toLocaleString() },
    { icon: 'analytics', color: '#6A1B9A', label: 'Acceptance Rate', value: stats?.acceptanceRate ?? '0%' },
  ];

  return (
    <ScrollView
      style={styles.container}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#2E7D32']} />}
    >
      {/* Welcome header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Welcome back,</Text>
          <Text style={styles.name}>{user?.name?.split(' ')[0] ?? 'User'}</Text>
        </View>
        <TouchableOpacity style={styles.profileBtn} onPress={() => navigation.navigate('Profile')}>
          <Ionicons name="person-circle" size={40} color="#2E7D32" />
        </TouchableOpacity>
      </View>

      {/* User code card */}
      <View style={styles.codeCard}>
        <Text style={styles.codeLabel}>Your User Code</Text>
        <Text style={styles.codeValue}>{user?.userCode ?? '------'}</Text>
        <Text style={styles.codeHint}>Enter this code at the disposal unit to earn points</Text>
        <View style={styles.earningBadge}>
          <Ionicons name="flash" size={13} color="#F57F17" />
          <Text style={styles.earningBadgeText}>{POINTS_PER_DISPOSAL} points per plastic bottle</Text>
        </View>
      </View>

      {/* Redemption progress */}
      {currentPoints < MIN_REDEEM ? (
        <View style={styles.progressCard}>
          <View style={styles.progressHeader}>
            <Text style={styles.progressTitle}>Progress to Redemption</Text>
            <Text style={styles.progressPts}>{currentPoints} / {MIN_REDEEM} pts</Text>
          </View>
          <View style={styles.progressBarBg}>
            <View style={[styles.progressBarFill, { width: `${progressToRedeem}%` }]} />
          </View>
          <Text style={styles.progressHint}>
            {disposalsToRedeem === 0
              ? 'Ready to redeem!'
              : `Dispose ${disposalsToRedeem} more bottle${disposalsToRedeem !== 1 ? 's' : ''} to unlock redemption`}
          </Text>
        </View>
      ) : (
        <TouchableOpacity style={styles.redeemReadyCard} onPress={() => navigation.navigate('Redeem')}>
          <Ionicons name="checkmark-circle" size={22} color="#fff" />
          <Text style={styles.redeemReadyText}>You have {currentPoints.toLocaleString()} pts — Ready to redeem airtime!</Text>
          <Ionicons name="chevron-forward" size={18} color="#fff" />
        </TouchableOpacity>
      )}

      {/* Stats grid */}
      <View style={styles.grid}>
        {cards.map((c, i) => (
          <View key={i} style={styles.statCard}>
            <Ionicons name={c.icon} size={24} color={c.color} />
            <Text style={styles.statValue}>{c.value}</Text>
            <Text style={styles.statLabel}>{c.label}</Text>
          </View>
        ))}
      </View>

      {/* Quick actions */}
      <Text style={styles.sectionTitle}>Quick Actions</Text>

      <TouchableOpacity style={styles.actionCard} onPress={() => navigation.navigate('Redeem')}>
        <View style={[styles.actionIcon, { backgroundColor: '#FFF8E1' }]}>
          <Ionicons name="send" size={22} color="#F57F17" />
        </View>
        <View style={styles.actionText}>
          <Text style={styles.actionTitle}>Redeem Airtime</Text>
          <Text style={styles.actionSub}>Convert your points to mobile airtime</Text>
        </View>
        <Ionicons name="chevron-forward" size={20} color="#ccc" />
      </TouchableOpacity>

      <TouchableOpacity style={styles.actionCard} onPress={() => navigation.navigate('History')}>
        <View style={[styles.actionIcon, { backgroundColor: '#E3F2FD' }]}>
          <Ionicons name="time" size={22} color="#1565C0" />
        </View>
        <View style={styles.actionText}>
          <Text style={styles.actionTitle}>Disposal History</Text>
          <Text style={styles.actionSub}>View your past recycling activity</Text>
        </View>
        <Ionicons name="chevron-forward" size={20} color="#ccc" />
      </TouchableOpacity>

      {/* Lifetime stats */}
      <View style={styles.lifetimeCard}>
        <Text style={styles.lifetimeTitle}>Lifetime Impact</Text>
        <View style={styles.lifetimeRow}>
          <View style={styles.lifetimeStat}>
            <Text style={styles.lifetimeValue}>{(stats?.totalSessions ?? 0).toLocaleString()}</Text>
            <Text style={styles.lifetimeLabel}>Sessions</Text>
          </View>
          <View style={styles.lifetimeDivider} />
          <View style={styles.lifetimeStat}>
            <Text style={styles.lifetimeValue}>{(stats?.acceptedItems ?? 0).toLocaleString()}</Text>
            <Text style={styles.lifetimeLabel}>Bottles Recycled</Text>
          </View>
          <View style={styles.lifetimeDivider} />
          <View style={styles.lifetimeStat}>
            <Text style={styles.lifetimeValue}>{(balance?.lifetimePoints ?? 0).toLocaleString()}</Text>
            <Text style={styles.lifetimeLabel}>Points Earned</Text>
          </View>
        </View>
      </View>

      {/* How it works */}
      <View style={styles.howCard}>
        <Text style={styles.howTitle}>How It Works</Text>
        <View style={styles.howStep}>
          <View style={styles.howNum}><Text style={styles.howNumText}>1</Text></View>
          <Text style={styles.howText}>Visit an EcoLens disposal unit near you</Text>
        </View>
        <View style={styles.howStep}>
          <View style={styles.howNum}><Text style={styles.howNumText}>2</Text></View>
          <Text style={styles.howText}>Enter your user code on the kiosk screen</Text>
        </View>
        <View style={styles.howStep}>
          <View style={styles.howNum}><Text style={styles.howNumText}>3</Text></View>
          <Text style={styles.howText}>Insert a plastic bottle — earn {POINTS_PER_DISPOSAL} points instantly</Text>
        </View>
        <View style={styles.howStep}>
          <View style={styles.howNum}><Text style={styles.howNumText}>4</Text></View>
          <Text style={styles.howText}>Redeem points for MTN or Airtel airtime</Text>
        </View>
      </View>

      <View style={{ height: 30 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F0' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#F5F5F0' },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 20, paddingTop: 16 },
  greeting: { fontSize: 14, color: '#888' },
  name: { fontSize: 24, fontWeight: '700', color: '#1B5E20' },
  profileBtn: { padding: 4 },
  codeCard: { backgroundColor: '#1B5E20', marginHorizontal: 20, borderRadius: 16, padding: 20, alignItems: 'center' },
  codeLabel: { color: '#A5D6A7', fontSize: 12, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 1 },
  codeValue: { color: '#fff', fontSize: 36, fontWeight: '700', marginVertical: 8, letterSpacing: 4 },
  codeHint: { color: '#A5D6A7', fontSize: 12 },
  earningBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.15)', borderRadius: 20, paddingHorizontal: 12, paddingVertical: 5, marginTop: 10, gap: 4 },
  earningBadgeText: { color: '#FFE082', fontSize: 12, fontWeight: '600' },
  progressCard: { backgroundColor: '#fff', marginHorizontal: 20, marginTop: 14, borderRadius: 14, padding: 16 },
  progressHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 10 },
  progressTitle: { fontSize: 13, fontWeight: '600', color: '#333' },
  progressPts: { fontSize: 13, fontWeight: '700', color: '#2E7D32' },
  progressBarBg: { height: 8, backgroundColor: '#E8F5E9', borderRadius: 99, overflow: 'hidden' },
  progressBarFill: { height: '100%', backgroundColor: '#2E7D32', borderRadius: 99 },
  progressHint: { fontSize: 11, color: '#888', marginTop: 8 },
  redeemReadyCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#F57F17', marginHorizontal: 20, marginTop: 14, borderRadius: 14, padding: 14, gap: 10 },
  redeemReadyText: { flex: 1, color: '#fff', fontWeight: '600', fontSize: 13 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', paddingHorizontal: 14, marginTop: 16 },
  statCard: { width: '46%', backgroundColor: '#fff', margin: '2%', borderRadius: 14, padding: 16, alignItems: 'center' },
  statValue: { fontSize: 22, fontWeight: '700', color: '#222', marginTop: 8 },
  statLabel: { fontSize: 12, color: '#888', marginTop: 4, textAlign: 'center' },
  sectionTitle: { fontSize: 18, fontWeight: '700', color: '#333', paddingHorizontal: 20, marginTop: 24, marginBottom: 12 },
  actionCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', marginHorizontal: 20, marginBottom: 10, borderRadius: 14, padding: 16 },
  actionIcon: { width: 44, height: 44, borderRadius: 12, justifyContent: 'center', alignItems: 'center', marginRight: 14 },
  actionText: { flex: 1 },
  actionTitle: { fontSize: 15, fontWeight: '600', color: '#222' },
  actionSub: { fontSize: 12, color: '#888', marginTop: 2 },
  lifetimeCard: { backgroundColor: '#fff', marginHorizontal: 20, marginTop: 20, borderRadius: 14, padding: 20 },
  lifetimeTitle: { fontSize: 16, fontWeight: '700', color: '#333', marginBottom: 16, textAlign: 'center' },
  lifetimeRow: { flexDirection: 'row', justifyContent: 'space-around', alignItems: 'center' },
  lifetimeStat: { alignItems: 'center' },
  lifetimeValue: { fontSize: 22, fontWeight: '700', color: '#2E7D32' },
  lifetimeLabel: { fontSize: 11, color: '#888', marginTop: 4, textAlign: 'center' },
  lifetimeDivider: { width: 1, height: 36, backgroundColor: '#eee' },
  howCard: { backgroundColor: '#fff', marginHorizontal: 20, marginTop: 16, borderRadius: 14, padding: 16 },
  howTitle: { fontSize: 15, fontWeight: '700', color: '#333', marginBottom: 14 },
  howStep: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  howNum: { width: 24, height: 24, borderRadius: 12, backgroundColor: '#E8F5E9', justifyContent: 'center', alignItems: 'center', marginRight: 12 },
  howNumText: { fontSize: 12, fontWeight: '700', color: '#2E7D32' },
  howText: { flex: 1, fontSize: 13, color: '#555', lineHeight: 18 },
});
