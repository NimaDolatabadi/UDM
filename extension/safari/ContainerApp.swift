// Containing app for the UDM Capture Safari extension.
//
// Safari loads web extensions only from inside an app. Opening this app shows
// the extension in Safari's settings, where the user turns it on, then quits.

import Foundation
import SafariServices

let extensionIdentifier = (Bundle.main.bundleIdentifier ?? "com.udm.manager.safari") + ".extension"
SFSafariApplication.showPreferencesForExtension(withIdentifier: extensionIdentifier) { _ in
    exit(0)
}
// Quit even when Safari never answers.
DispatchQueue.main.asyncAfter(deadline: .now() + 10) { exit(0) }
dispatchMain()
