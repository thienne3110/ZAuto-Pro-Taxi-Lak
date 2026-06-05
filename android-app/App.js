import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  StyleSheet,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  Alert,
  Switch,
  ScrollView,
  ActivityIndicator,
  Vibration,
  Image,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { io } from "socket.io-client";
import * as Notifications from "expo-notifications";
import { StatusBar } from "expo-status-bar";

// ─── Cấu hình thông báo ──────────────────────────────────────────────────────
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

const STORAGE_KEY_SERVER = "zauto_server_url";
const DEFAULT_SERVER = "http://192.168.1.100:3000";

// ─── App chính ────────────────────────────────────────────────────────────────
export default function App() {
  const [tab, setTab] = useState("home");
  const [serverUrl, setServerUrl] = useState(DEFAULT_SERVER);
  const [serverUrlInput, setServerUrlInput] = useState(DEFAULT_SERVER);
  const [connected, setConnected] = useState(false);
  const [zaloStatus, setZaloStatus] = useState("waiting");
  const [qrBase64, setQrBase64] = useState(null);
  const [messages, setMessages] = useState([]);
  const [autoMode, setAutoMode] = useState(true);
  const [keywords, setKeywords] = useState("đón*trả*giá");
  const [replyMsg, setReplyMsg] = useState("ok nhận");
  const [loading, setLoading] = useState(false);
  const socketRef = useRef(null);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY_SERVER).then((saved) => {
      if (saved) {
        setServerUrl(saved);
        setServerUrlInput(saved);
      }
    });
    requestNotificationPermission();
  }, []);

  const requestNotificationPermission = async () => {
    const { status } = await Notifications.requestPermissionsAsync();
    if (status !== "granted") {
      Alert.alert("Thông báo", "Cần bật quyền thông báo để nhận cảnh báo cuốc xe.");
    }
  };

  const connect = useCallback(() => {
    if (socketRef.current) socketRef.current.disconnect();
    setLoading(true);

    const socket = io(serverUrl, {
      transports: ["websocket"],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 2000,
      timeout: 10000,
    });

    socket.on("connect", () => {
      setConnected(true);
      setLoading(false);
      loadConfig(serverUrl);
    });

    socket.on("disconnect", () => {
      setConnected(false);
      setZaloStatus("waiting");
    });

    socket.on("connect_error", () => {
      setLoading(false);
      setConnected(false);
    });

    socket.on("zalo_status", ({ status }) => {
      setZaloStatus(status);
      if (status === "success") setQrBase64(null);
      else if (status === "pending") fetchQR(serverUrl);
    });

    socket.on("qr", ({ qrBase64: qr }) => setQrBase64(qr));

    socket.on("new_zalo_message", (payload) => {
      setMessages((prev) => [payload, ...prev].slice(0, 200));
      sendLocalNotification(payload);
      Vibration.vibrate(400);
    });

    socket.on("message_history", (history) => {
      setMessages(history.slice(0, 200));
    });

    socket.on("nhan_cuoc_thanh_cong", ({ messageId, auto }) => {
      setMessages((prev) =>
        prev.map((m) => (m.id === messageId ? { ...m, accepted: true, auto } : m))
      );
    });

    socket.on("nhan_cuoc_that_bai", ({ error: err }) => {
      Alert.alert("❌ Lỗi nhận cuốc", err);
    });

    socketRef.current = socket;
  }, [serverUrl]);

  useEffect(() => {
    connect();
    return () => socketRef.current?.disconnect();
  }, [connect]);

  const fetchQR = async (url = serverUrl) => {
    try {
      const res = await fetch(`${url}/api/get-qr`);
      const data = await res.json();
      if (data.qrBase64) setQrBase64(data.qrBase64);
    } catch (_) {}
  };

  const loadConfig = async (url = serverUrl) => {
    try {
      const res = await fetch(`${url}/api/config`);
      const data = await res.json();
      setAutoMode(data.autoModeEnabled);
      setKeywords(data.autoKeywords);
      setReplyMsg(data.replyMessage);
    } catch (_) {}
  };

  const saveConfig = async () => {
    try {
      await fetch(`${serverUrl}/api/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          autoModeEnabled: autoMode,
          autoKeywords: keywords,
          replyMessage: replyMsg,
        }),
      });
      Alert.alert("✅ Đã lưu cài đặt");
    } catch (_) {
      Alert.alert("❌ Không thể lưu cài đặt");
    }
  };

  const saveServerUrl = async () => {
    await AsyncStorage.setItem(STORAGE_KEY_SERVER, serverUrlInput);
    setServerUrl(serverUrlInput);
    Alert.alert("✅ Đã lưu. Đang kết nối lại...");
  };

  const nhanCuoc = (msg) => {
    if (!socketRef.current?.connected) {
      Alert.alert("❌ Chưa kết nối server");
      return;
    }
    socketRef.current.emit("nhan_cuoc", {
      groupId: msg.groupId,
      messageId: msg.id,
    });
  };

  const sendLocalNotification = async (payload) => {
    await Notifications.scheduleNotificationAsync({
      content: {
        title: `🚖 ${payload.groupName}`,
        body: payload.content,
        sound: true,
      },
      trigger: null,
    });
  };

  return (
    <View style={styles.root}>
      <StatusBar style="light" />

      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🚖 ZAuto Taxi Lak</Text>
        <View style={styles.headerRight}>
          <View style={[styles.dot, { backgroundColor: connected ? "#4ade80" : "#f87171" }]} />
          <Text style={styles.statusText}>
            {connected ? `Zalo: ${zaloStatus}` : "Mất kết nối"}
          </Text>
        </View>
      </View>

      {/* Tab bar */}
      <View style={styles.tabBar}>
        {[
          { key: "home", label: "🏠 Trang chủ" },
          { key: "messages", label: "💬 Tin nhắn" },
          { key: "settings", label: "⚙️ Cài đặt" },
        ].map((t) => (
          <TouchableOpacity
            key={t.key}
            style={[styles.tab, tab === t.key && styles.tabActive]}
            onPress={() => setTab(t.key)}
          >
            <Text style={[styles.tabText, tab === t.key && styles.tabTextActive]}>
              {t.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Nội dung */}
      {tab === "home" && (
        <HomeTab
          zaloStatus={zaloStatus}
          qrBase64={qrBase64}
          connected={connected}
          loading={loading}
          onRefreshQR={() => fetchQR()}
          onLogout={() => socketRef.current?.emit("logout")}
          messages={messages}
          onNhanCuoc={nhanCuoc}
        />
      )}
      {tab === "messages" && (
        <MessagesTab messages={messages} onNhanCuoc={nhanCuoc} />
      )}
      {tab === "settings" && (
        <SettingsTab
          serverUrlInput={serverUrlInput}
          setServerUrlInput={setServerUrlInput}
          onSaveServer={saveServerUrl}
          autoMode={autoMode}
          setAutoMode={setAutoMode}
          keywords={keywords}
          setKeywords={setKeywords}
          replyMsg={replyMsg}
          setReplyMsg={setReplyMsg}
          onSaveConfig={saveConfig}
        />
      )}
    </View>
  );
}

// ─── Tab Trang chủ ────────────────────────────────────────────────────────────
function HomeTab({ zaloStatus, qrBase64, connected, loading, onRefreshQR, onLogout, messages, onNhanCuoc }) {
  const recent = messages.slice(0, 5);

  const statusInfo = () => {
    if (!connected) return { text: "🔴 Chưa kết nối server", color: "#f87171" };
    if (zaloStatus === "success") return { text: "🟢 Zalo đã đăng nhập", color: "#4ade80" };
    if (zaloStatus === "pending") return { text: "🟡 Đang chờ quét QR", color: "#facc15" };
    if (zaloStatus === "scanned") return { text: "🟡 Đã quét, đang xác nhận...", color: "#facc15" };
    return { text: "⚪ Chờ kết nối Zalo", color: "#888" };
  };

  const { text, color } = statusInfo();

  return (
    <ScrollView style={styles.content} contentContainerStyle={{ paddingBottom: 30 }}>
      {/* Trạng thái */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📡 Trạng thái kết nối</Text>
        <Text style={[styles.statusBig, { color }]}>{text}</Text>
        {loading && <ActivityIndicator color="#e94560" style={{ marginTop: 10 }} />}
        {zaloStatus === "success" && connected && (
          <TouchableOpacity style={[styles.btn, { backgroundColor: "#dc2626", marginTop: 12 }]} onPress={onLogout}>
            <Text style={styles.btnText}>🔓 Đăng xuất Zalo</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* QR */}
      {connected && (zaloStatus === "pending" || zaloStatus === "waiting") && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>📲 Quét QR để đăng nhập Zalo</Text>
          {qrBase64 ? (
            <Image
              source={{ uri: qrBase64 }}
              style={{ width: 220, height: 220, alignSelf: "center", marginTop: 10, borderRadius: 8 }}
              resizeMode="contain"
            />
          ) : (
            <Text style={styles.hint}>Đang tải mã QR...</Text>
          )}
          <TouchableOpacity style={[styles.btn, { marginTop: 12 }]} onPress={onRefreshQR}>
            <Text style={styles.btnText}>🔄 Làm mới QR</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Cuốc xe gần nhất */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📨 Cuốc xe gần nhất</Text>
        {recent.length === 0 ? (
          <Text style={styles.hint}>Chưa có tin nhắn nào.</Text>
        ) : (
          recent.map((m) => <MessageCard key={m.id} msg={m} onNhanCuoc={onNhanCuoc} />)
        )}
      </View>
    </ScrollView>
  );
}

// ─── Tab Tin nhắn ─────────────────────────────────────────────────────────────
function MessagesTab({ messages, onNhanCuoc }) {
  return (
    <FlatList
      style={styles.content}
      data={messages}
      keyExtractor={(m) => String(m.id)}
      renderItem={({ item }) => <MessageCard msg={item} onNhanCuoc={onNhanCuoc} />}
      ListEmptyComponent={
        <Text style={[styles.hint, { textAlign: "center", marginTop: 40 }]}>
          Chưa có tin nhắn nào.
        </Text>
      }
      contentContainerStyle={{ padding: 12, paddingBottom: 30 }}
    />
  );
}

// ─── Card tin nhắn ────────────────────────────────────────────────────────────
function MessageCard({ msg, onNhanCuoc }) {
  return (
    <View style={[styles.msgCard, msg.accepted && styles.msgCardAccepted]}>
      <Text style={styles.groupName}>👥 {msg.groupName}</Text>
      <Text style={styles.msgContent}>{msg.content}</Text>
      {msg.accepted ? (
        <Text style={styles.acceptedBadge}>
          {msg.auto ? "✅ Tự động nhận" : "✅ Đã nhận thủ công"}
        </Text>
      ) : (
        <TouchableOpacity
          style={[styles.btn, { backgroundColor: "#0ea5e9" }]}
          onPress={() => onNhanCuoc(msg)}
        >
          <Text style={styles.btnText}>🚖 Nhận cuốc này</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

// ─── Tab Cài đặt ──────────────────────────────────────────────────────────────
function SettingsTab({
  serverUrlInput, setServerUrlInput, onSaveServer,
  autoMode, setAutoMode,
  keywords, setKeywords,
  replyMsg, setReplyMsg,
  onSaveConfig,
}) {
  return (
    <ScrollView style={styles.content} contentContainerStyle={{ paddingBottom: 40 }}>

      {/* Server */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🌐 Địa chỉ Server</Text>
        <Text style={styles.hint}>
          Nhập IP máy tính đang chạy server Node.js (phải cùng WiFi với điện thoại)
        </Text>
        <TextInput
          style={styles.input}
          value={serverUrlInput}
          onChangeText={setServerUrlInput}
          placeholder="http://192.168.x.x:3000"
          placeholderTextColor="#555"
          autoCapitalize="none"
          keyboardType="url"
        />
        <TouchableOpacity style={styles.btn} onPress={onSaveServer}>
          <Text style={styles.btnText}>💾 Lưu & kết nối lại</Text>
        </TouchableOpacity>
      </View>

      {/* Auto mode */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>🤖 Tự động nhận cuốc</Text>

        <View style={styles.row}>
          <Text style={styles.label}>Bật chế độ tự động</Text>
          <Switch
            value={autoMode}
            onValueChange={setAutoMode}
            trackColor={{ false: "#333", true: "#e94560" }}
            thumbColor="#fff"
          />
        </View>

        <Text style={styles.label}>Từ khóa (cách nhau bởi * hoặc ,)</Text>
        <TextInput
          style={styles.input}
          value={keywords}
          onChangeText={setKeywords}
          placeholder="đón*trả*giá"
          placeholderTextColor="#555"
        />

        <Text style={styles.label}>Tin nhắn phản hồi tự động</Text>
        <TextInput
          style={styles.input}
          value={replyMsg}
          onChangeText={setReplyMsg}
          placeholder="ok nhận"
          placeholderTextColor="#555"
        />

        <TouchableOpacity style={styles.btn} onPress={onSaveConfig}>
          <Text style={styles.btnText}>💾 Lưu cài đặt</Text>
        </TouchableOpacity>
      </View>

      {/* Hướng dẫn */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📖 Hướng dẫn sử dụng</Text>
        <Text style={styles.hint}>1. Chạy server Node.js trên máy tính</Text>
        <Text style={styles.hint}>2. Điền IP máy tính vào ô trên</Text>
        <Text style={styles.hint}>3. Quét QR Zalo ở tab Trang chủ</Text>
        <Text style={styles.hint}>4. Bot sẽ tự nhận cuốc khi có từ khóa khớp</Text>
        <Text style={styles.hint}>5. Hoặc bấm "Nhận cuốc" để nhận thủ công</Text>
      </View>
    </ScrollView>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────
const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#0f0f1a",
  },
  header: {
    backgroundColor: "#1a1a2e",
    paddingTop: 48,
    paddingBottom: 14,
    paddingHorizontal: 16,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderBottomWidth: 1,
    borderBottomColor: "#e94560",
  },
  headerTitle: {
    color: "#e94560",
    fontSize: 20,
    fontWeight: "bold",
  },
  headerRight: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  statusText: {
    color: "#ccc",
    fontSize: 12,
  },
  tabBar: {
    flexDirection: "row",
    backgroundColor: "#16213e",
    borderBottomWidth: 1,
    borderBottomColor: "#1e2d4a",
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    alignItems: "center",
  },
  tabActive: {
    borderBottomWidth: 2,
    borderBottomColor: "#e94560",
  },
  tabText: {
    color: "#888",
    fontSize: 12,
  },
  tabTextActive: {
    color: "#e94560",
    fontWeight: "bold",
  },
  content: {
    flex: 1,
    padding: 12,
  },
  card: {
    backgroundColor: "#1a1a2e",
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: "#1e2d4a",
  },
  cardTitle: {
    color: "#e94560",
    fontSize: 15,
    fontWeight: "bold",
    marginBottom: 10,
  },
  statusBig: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 4,
  },
  hint: {
    color: "#666",
    fontSize: 13,
    marginTop: 4,
    lineHeight: 20,
  },
  msgCard: {
    backgroundColor: "#16213e",
    borderRadius: 10,
    padding: 14,
    marginBottom: 10,
    borderLeftWidth: 3,
    borderLeftColor: "#e94560",
  },
  msgCardAccepted: {
    borderLeftColor: "#4ade80",
    opacity: 0.75,
  },
  groupName: {
    color: "#a0a0c0",
    fontSize: 12,
    marginBottom: 4,
  },
  msgContent: {
    color: "#fff",
    fontSize: 15,
    marginBottom: 10,
    lineHeight: 22,
  },
  acceptedBadge: {
    color: "#4ade80",
    fontSize: 13,
    fontWeight: "600",
  },
  btn: {
    backgroundColor: "#e94560",
    borderRadius: 8,
    paddingVertical: 11,
    paddingHorizontal: 16,
    alignItems: "center",
    marginTop: 8,
  },
  btnText: {
    color: "#fff",
    fontWeight: "bold",
    fontSize: 14,
  },
  input: {
    backgroundColor: "#0f0f1a",
    color: "#fff",
    borderRadius: 8,
    padding: 11,
    marginTop: 6,
    marginBottom: 6,
    borderWidth: 1,
    borderColor: "#2a2a4a",
    fontSize: 14,
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 14,
  },
  label: {
    color: "#ccc",
    fontSize: 14,
    marginBottom: 4,
    marginTop: 8,
  },
});
