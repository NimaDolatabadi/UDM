// Safari extension handler that relays UDM Capture messages to the UDM app.
//
// Safari has no native-messaging hosts. It delivers
// `browser.runtime.sendNativeMessage` to this app extension instead, so this
// file does the job of udm/bridge/native_host.py: it forwards each message to
// the app's bridge socket and starts UDM when it is not running. The install
// step in udm/bridge/safari.py records the socket path (UDMBridgeSocket) and
// the app bundle (UDMAppPath) in Info.plist.

import AppKit
import Foundation
import SafariServices

@objc(SafariWebExtensionHandler)
final class SafariWebExtensionHandler: NSObject, NSExtensionRequestHandling {
    func beginRequest(with context: NSExtensionContext) {
        let item = context.inputItems.first as? NSExtensionItem
        let message = item?.userInfo?[SFExtensionMessageKey] as? [String: Any] ?? [:]
        // Sockets block, so the reply is built off the extension's main queue.
        DispatchQueue.global(qos: .userInitiated).async {
            let response = NSExtensionItem()
            response.userInfo = [SFExtensionMessageKey: Bridge(bundle: .main).handle(message)]
            context.completeRequest(returningItems: [response], completionHandler: nil)
        }
    }
}

enum BridgeFailure: Error {
    /// Nothing listens on the socket; the request was never delivered.
    case unreachable
    /// The request was sent but the reply was missing or malformed.
    case badReply
}

struct Bridge {
    static let launchTimeout: TimeInterval = 20
    static let maxReplyBytes = 8 * 1024 * 1024

    let socketPath: String
    let appPath: String

    init(bundle: Bundle) {
        socketPath = bundle.object(forInfoDictionaryKey: "UDMBridgeSocket") as? String ?? ""
        appPath = bundle.object(forInfoDictionaryKey: "UDMAppPath") as? String ?? ""
    }

    /// Return the reply for one extension message, mirroring native_host.handle.
    func handle(_ message: [String: Any]) -> [String: Any] {
        let kind = message["type"] as? String
        if kind == "ping" {
            guard let reply = try? send(message, timeout: 2) else {
                return ["ok": true, "host": true, "running": false]
            }
            return reply.merging(["host": true]) { _, host in host }
        }
        // The app resolves qualities with yt-dlp, which takes several seconds.
        let timeout: TimeInterval = kind == "formats" ? 90 : 5
        do {
            return try forward(message, timeout: timeout)
        } catch BridgeFailure.badReply {
            return ["ok": false, "error": "UDM sent an invalid reply"]
        } catch {
            return ["ok": false, "error": "UDM is not running and could not start"]
        }
    }

    private func forward(_ message: [String: Any], timeout: TimeInterval) throws -> [String: Any] {
        do {
            return try send(message, timeout: timeout)
        } catch BridgeFailure.unreachable {
            guard launchApp() else { throw BridgeFailure.unreachable }
        }
        let deadline = Date().addingTimeInterval(Bridge.launchTimeout)
        while true {
            do {
                return try send(message, timeout: timeout)
            } catch BridgeFailure.unreachable where Date() < deadline {
                Thread.sleep(forTimeInterval: 0.25)
            }
        }
    }

    /// Send one JSON line and read one JSON line back.
    func send(_ message: [String: Any], timeout: TimeInterval) throws -> [String: Any] {
        guard JSONSerialization.isValidJSONObject(message),
              var payload = try? JSONSerialization.data(withJSONObject: message) else {
            throw BridgeFailure.badReply
        }
        payload.append(0x0A)
        let descriptor = try connect(timeout: timeout)
        defer { close(descriptor) }
        let written = payload.withUnsafeBytes { write(descriptor, $0.baseAddress, payload.count) }
        guard written == payload.count else { throw BridgeFailure.badReply }
        var buffer = Data()
        var chunk = [UInt8](repeating: 0, count: 65536)
        while !buffer.contains(0x0A) {
            let count = read(descriptor, &chunk, chunk.count)
            if count <= 0 { break }
            buffer.append(contentsOf: chunk[0..<count])
            if buffer.count > Bridge.maxReplyBytes { throw BridgeFailure.badReply }
        }
        let line = buffer.split(separator: 0x0A, maxSplits: 1).first ?? Data()
        guard let reply = try? JSONSerialization.jsonObject(with: line) as? [String: Any] else {
            throw BridgeFailure.badReply
        }
        return reply
    }

    private func connect(timeout: TimeInterval) throws -> Int32 {
        var address = sockaddr_un()
        let capacity = MemoryLayout.size(ofValue: address.sun_path)
        guard !socketPath.isEmpty, socketPath.utf8.count < capacity else {
            throw BridgeFailure.unreachable
        }
        address.sun_family = sa_family_t(AF_UNIX)
        withUnsafeMutableBytes(of: &address.sun_path) { raw in
            raw.copyBytes(from: socketPath.utf8)
        }
        let descriptor = socket(AF_UNIX, SOCK_STREAM, 0)
        guard descriptor >= 0 else { throw BridgeFailure.unreachable }
        var limit = timeval(tv_sec: Int(timeout), tv_usec: 0)
        let size = socklen_t(MemoryLayout<timeval>.size)
        setsockopt(descriptor, SOL_SOCKET, SO_RCVTIMEO, &limit, size)
        setsockopt(descriptor, SOL_SOCKET, SO_SNDTIMEO, &limit, size)
        let result = withUnsafePointer(to: &address) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                Darwin.connect(descriptor, $0, socklen_t(MemoryLayout<sockaddr_un>.size))
            }
        }
        guard result == 0 else {
            close(descriptor)
            throw BridgeFailure.unreachable
        }
        return descriptor
    }

    /// Open UDM through Launch Services; false for source runs without a bundle.
    private func launchApp() -> Bool {
        guard !appPath.isEmpty else { return false }
        let done = DispatchSemaphore(value: 0)
        var launched = false
        NSWorkspace.shared.openApplication(
            at: URL(fileURLWithPath: appPath),
            configuration: NSWorkspace.OpenConfiguration()
        ) { app, _ in
            launched = app != nil
            done.signal()
        }
        _ = done.wait(timeout: .now() + 10)
        return launched
    }
}
