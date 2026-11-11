// WORKS (VINFILM STUDIO 작업 관리) — 대표님용 아이폰 앱. www.vinfilmstudio.com/works/ 를 앱 화면으로 띄우고 애플 푸시(APNs)를 받는다.
// 틀은 HISPLAN 'WORK' 앱(hisplan-app)과 같다. 다른 점: 주소, 외부 링크는 앱 안 사파리 창, 우리 사이트 팝업(견적서 미리보기 등)엔 닫기 버튼,
// 당겨서 새로고침 없음(입력 중인 창이 실수로 새로고침되는 걸 막음), 오래 쉬다 돌아오면 새로 읽기.
import SwiftUI
import WebKit
import SafariServices
import UserNotifications

@main
struct WorksApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    var body: some Scene {
        WindowGroup { WebScreen().ignoresSafeArea(edges: .bottom).background(Color.black) }
    }
}

struct WebScreen: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> WebVC { WebVC() }
    func updateUIViewController(_ vc: WebVC, context: Context) {}
}

// ── 푸시 알림 (애플 푸시) ──────────────────────────────────────────────
// 사이트(works/index.html)와 약속:
//   앱 → 웹: window.__workApp.push = { permission, token, env } 를 적고 'workapp:push' 이벤트를 보낸다
//   웹 → 앱: window.webkit.messageHandlers.workApp.postMessage({ type: 'enablePush' | 'badge' | 'openSettings' })
// 사이트가 토큰을 Firestore pushSubs 에 적고, 보내는 쪽(Mac 스튜디오 다리의 push.mjs)이 애플로 알림을 보낸다.
final class AppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {
    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        UNUserNotificationCenter.current().delegate = self
        Task { await Push.shared.refresh() }
        return true
    }

    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        Push.shared.token = deviceToken.map { String(format: "%02x", $0) }.joined()
        Push.shared.publish()
    }

    func application(_ application: UIApplication, didFailToRegisterForRemoteNotificationsWithError error: Error) {
        print("push register failed", error)
        Push.shared.publish()
    }

    // 앱을 보고 있을 때도 배너로 보여 준다
    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter,
                                            willPresent notification: UNNotification) async -> UNNotificationPresentationOptions {
        [.banner, .list, .sound, .badge]
    }

    // 알림을 누르면 그 알림의 화면(link)을 연다
    nonisolated func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse) async {
        let link = response.notification.request.content.userInfo["link"] as? String
        await MainActor.run { Push.shared.open(link) }
    }
}

@MainActor final class Push {
    static let shared = Push()
    weak var web: WKWebView?
    var permission = "notDetermined"
    var pendingURL: URL?
    var token: String? {
        get { UserDefaults.standard.string(forKey: "apnsToken") }
        set { UserDefaults.standard.set(newValue, forKey: "apnsToken") }
    }
    #if DEBUG
    let env = "sandbox"
    #else
    let env = "production"
    #endif

    func refresh() async {
        let s = await UNUserNotificationCenter.current().notificationSettings()
        switch s.authorizationStatus {
        case .authorized, .provisional, .ephemeral: permission = "granted"
        case .denied: permission = "denied"
        default: permission = "notDetermined"
        }
        if permission == "granted" { UIApplication.shared.registerForRemoteNotifications() }
        publish()
    }

    // 사이트의 '알림 켜기' 버튼 → 아이폰 알림 허용 창
    func request() {
        Task {
            _ = try? await UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge])
            await refresh()
        }
    }

    private var stateJSON: String {
        let obj: [String: Any] = ["permission": permission, "token": token ?? NSNull(), "env": env]
        let data = (try? JSONSerialization.data(withJSONObject: obj)) ?? Data("{}".utf8)
        return String(data: data, encoding: .utf8) ?? "{}"
    }

    // 페이지가 처음 뜰 때 넣는 값 (이후 바뀌면 publish 로 알려 준다)
    var bootScript: String { "window.__workApp={platform:'ios',push:\(stateJSON)};" }

    func publish() {
        web?.evaluateJavaScript("window.__workApp=Object.assign(window.__workApp||{platform:'ios'},{push:\(stateJSON)});window.dispatchEvent(new Event('workapp:push'));")
    }

    func open(_ link: String?) {
        guard let link, let url = URL(string: link, relativeTo: WebVC.home)?.absoluteURL,
              url.host?.lowercased().hasSuffix("vinfilmstudio.com") == true else { return }
        if let web { web.load(URLRequest(url: url)) } else { pendingURL = url }
    }
}

final class WebVC: UIViewController, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler {
    static let home = URL(string: "https://www.vinfilmstudio.com/works/")!
    private var web: WKWebView!
    private var popup: WKWebView?
    private var popupBox: UIView?
    private var leftAt: Date?

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .black
        let cfg = WKWebViewConfiguration()
        cfg.allowsInlineMediaPlayback = true
        cfg.websiteDataStore = .default()
        // 구글 로그인은 앱 안 웹 화면을 막으므로 사파리라고 알림
        cfg.applicationNameForUserAgent = "Version/18.0 Mobile/15E148 Safari/604.1"
        // 사이트와 주고받기 (푸시 토큰·아이콘 숫자)
        cfg.userContentController.add(self, name: "workApp")
        cfg.userContentController.addUserScript(WKUserScript(source: Push.shared.bootScript, injectionTime: .atDocumentStart, forMainFrameOnly: true))
        web = WKWebView(frame: view.bounds, configuration: cfg)
        web.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        web.navigationDelegate = self
        web.uiDelegate = self
        // WORKS 화면에 자체 '왼쪽 가장자리 밀기 = 뒤로'가 있어서 기본 뒤로가기 제스처는 끈다
        web.allowsBackForwardNavigationGestures = false
        web.isOpaque = false
        web.backgroundColor = .black
        view.addSubview(web)
        Push.shared.web = web
        // 알림을 눌러 앱이 켜졌으면 그 화면부터
        web.load(URLRequest(url: Push.shared.pendingURL ?? Self.home))
        Push.shared.pendingURL = nil
        // 설정 앱에서 알림을 바꾸고 돌아올 수 있다 / 오래 쉬다 돌아오면 최신 화면으로
        NotificationCenter.default.addObserver(forName: UIApplication.didEnterBackgroundNotification, object: nil, queue: .main) { [weak self] _ in
            self?.leftAt = Date()
        }
        NotificationCenter.default.addObserver(forName: UIApplication.didBecomeActiveNotification, object: nil, queue: .main) { [weak self] _ in
            Task { await Push.shared.refresh() }
            if let t = self?.leftAt, Date().timeIntervalSince(t) > 20 * 60 { self?.web.reloadFromOrigin() }
            self?.leftAt = nil
        }
    }

    // 페이지를 새로 읽을 때마다 최신 알림 상태를 다시 알려 준다 (처음 넣은 값은 오래됐을 수 있다)
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        if webView === web { Push.shared.publish() }
    }

    // 앱 화면이 메모 부족으로 꺼지면 하얀 화면이 되므로 다시 읽는다
    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) { webView.reload() }

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard let body = message.body as? [String: Any], let type = body["type"] as? String else { return }
        switch type {
        case "enablePush":
            Push.shared.request()
        case "badge":
            let n = (body["count"] as? NSNumber)?.intValue ?? 0
            UNUserNotificationCenter.current().setBadgeCount(n)
            if n == 0 { UNUserNotificationCenter.current().removeAllDeliveredNotifications() }
        case "openSettings":
            if let url = URL(string: UIApplication.openSettingsURLString) { UIApplication.shared.open(url) }
        default:
            break
        }
    }

    override var preferredStatusBarStyle: UIStatusBarStyle { .lightContent }

    // 앱 화면 안에서 그대로 열 사이트 (우리 사이트 + 로그인에 쓰는 구글·파이어베이스)
    private static func isInApp(_ host: String) -> Bool {
        host.hasSuffix("vinfilmstudio.com") || host.hasSuffix("firebaseapp.com") || host.hasSuffix("web.app")
            || host.hasSuffix("google.com") || host.hasSuffix("googleapis.com") || host.hasSuffix("gstatic.com")
    }

    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                 decisionHandler: @escaping @MainActor (WKNavigationActionPolicy) -> Void) {
        guard let url = action.request.url, let scheme = url.scheme?.lowercased() else { decisionHandler(.allow); return }
        // 다른 앱으로 가는 주소(webcal://, kakaotalk://, 전화·메일 등)는 밖으로
        if !["http", "https", "about", "blob", "data", "javascript"].contains(scheme) {
            UIApplication.shared.open(url)
            decisionHandler(.cancel); return
        }
        // 다른 사이트 링크를 직접 누르면 앱 안 사파리 창으로
        if action.navigationType == .linkActivated, action.targetFrame?.isMainFrame ?? true,
           !Self.isInApp(url.host?.lowercased() ?? "") {
            present(SFSafariViewController(url: url), animated: true)
            decisionHandler(.cancel); return
        }
        decisionHandler(.allow)
    }

    // 새 창(window.open / target=_blank): 다른 사이트는 앱 안 사파리 창으로,
    // 로그인 팝업·견적서 미리보기처럼 우리 쪽 창은 위에 덮는 창(닫기 버튼 포함)으로
    func webView(_ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
                 for action: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
        if let url = action.request.url, let scheme = url.scheme?.lowercased(), ["http", "https"].contains(scheme),
           let host = url.host?.lowercased(), !Self.isInApp(host) {
            present(SFSafariViewController(url: url), animated: true)
            return nil
        }
        closePopup()
        let box = UIView(frame: view.bounds)
        box.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        box.backgroundColor = .black
        let p = WKWebView(frame: box.bounds, configuration: configuration)
        p.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        p.navigationDelegate = self
        p.uiDelegate = self
        p.customUserAgent = webView.customUserAgent
        box.addSubview(p)
        var bc = UIButton.Configuration.filled()
        bc.title = "닫기"
        bc.baseBackgroundColor = UIColor(white: 0, alpha: 0.65)
        bc.baseForegroundColor = .white
        bc.cornerStyle = .capsule
        let close = UIButton(configuration: bc, primaryAction: UIAction { [weak self] _ in self?.closePopup() })
        close.translatesAutoresizingMaskIntoConstraints = false
        box.addSubview(close)
        NSLayoutConstraint.activate([
            close.topAnchor.constraint(equalTo: box.topAnchor, constant: 8),
            close.trailingAnchor.constraint(equalTo: box.trailingAnchor, constant: -8),
        ])
        view.addSubview(box)
        popup = p
        popupBox = box
        return p
    }

    func webViewDidClose(_ webView: WKWebView) {
        if webView === popup { closePopup() }
    }

    private func closePopup() {
        popupBox?.removeFromSuperview()
        popupBox = nil
        popup = nil
    }

    func webView(_ webView: WKWebView, runJavaScriptAlertPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo,
                 completionHandler: @escaping @MainActor () -> Void) {
        let a = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        a.addAction(UIAlertAction(title: "확인", style: .default) { _ in completionHandler() })
        present(a, animated: true)
    }

    func webView(_ webView: WKWebView, runJavaScriptConfirmPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo,
                 completionHandler: @escaping @MainActor (Bool) -> Void) {
        let a = UIAlertController(title: nil, message: message, preferredStyle: .alert)
        a.addAction(UIAlertAction(title: "취소", style: .cancel) { _ in completionHandler(false) })
        a.addAction(UIAlertAction(title: "확인", style: .default) { _ in completionHandler(true) })
        present(a, animated: true)
    }

    func webView(_ webView: WKWebView, runJavaScriptTextInputPanelWithPrompt prompt: String, defaultText: String?,
                 initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping @MainActor (String?) -> Void) {
        let a = UIAlertController(title: nil, message: prompt, preferredStyle: .alert)
        a.addTextField { $0.text = defaultText }
        a.addAction(UIAlertAction(title: "취소", style: .cancel) { _ in completionHandler(nil) })
        a.addAction(UIAlertAction(title: "확인", style: .default) { _ in completionHandler(a.textFields?.first?.text) })
        present(a, animated: true)
    }

    // 파일 받기(견적서 PDF·첨부파일 등)는 공유 창으로
    func webView(_ webView: WKWebView, decidePolicyFor response: WKNavigationResponse,
                 decisionHandler: @escaping @MainActor (WKNavigationResponsePolicy) -> Void) {
        if let r = response.response as? HTTPURLResponse,
           (r.value(forHTTPHeaderField: "Content-Disposition") ?? "").lowercased().contains("attachment") {
            decisionHandler(.download); return
        }
        decisionHandler(.allow)
    }

    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) { download.delegate = self }
    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) { download.delegate = self }
}

extension WebVC: WKDownloadDelegate {
    func download(_ download: WKDownload, decideDestinationUsing response: URLResponse, suggestedFilename: String,
                  completionHandler: @escaping @MainActor (URL?) -> Void) {
        let u = FileManager.default.temporaryDirectory.appendingPathComponent(suggestedFilename)
        try? FileManager.default.removeItem(at: u)
        objc_setAssociatedObject(download, &WebVC.dlKey, u, .OBJC_ASSOCIATION_RETAIN)
        completionHandler(u)
    }
    func downloadDidFinish(_ download: WKDownload) {
        guard let u = objc_getAssociatedObject(download, &WebVC.dlKey) as? URL else { return }
        let vc = UIActivityViewController(activityItems: [u], applicationActivities: nil)
        vc.popoverPresentationController?.sourceView = view
        present(vc, animated: true)
    }
    nonisolated(unsafe) static var dlKey = 0
}
