const vscode = require('vscode');
const WebSocket = require('ws');

let ws = null;
let statusStatusBarItem = null;

function activate(context) {
    console.log('DevMind Bridge is now active!');

    // Status bar item to show bridge status
    statusStatusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusStatusBarItem.text = '$(debug-disconnect) DevMind: Offline';
    statusStatusBarItem.tooltip = 'Click to connect to local DevMind agent';
    statusStatusBarItem.command = 'devmind.connect';
    statusStatusBarItem.show();
    context.subscriptions.push(statusStatusBarItem);

    // Register sidebar chat webview provider
    const sidebarProvider = new DevMindChatViewProvider(context.extensionUri);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            'devmind.chatView',
            sidebarProvider
        )
    );

    // Connect command
    const connectCmd = vscode.commands.registerCommand('devmind.connect', () => {
        connectToAgent();
    });
    context.subscriptions.push(connectCmd);

    // Undo command
    const undoCmd = vscode.commands.registerCommand('devmind.undo', () => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'chat', content: '/undo' }));
            vscode.window.showInformationMessage('Requested DevMind to undo last edit.');
        } else {
            vscode.window.showErrorMessage('DevMind is not connected.');
        }
    });
    context.subscriptions.push(undoCmd);

    // Auto-connect on start
    connectToAgent();

    // Listen for editor focus change
    vscode.window.onDidChangeActiveTextEditor(editor => {
        sendActiveEditorContext(editor);
    });

    // Listen for document save
    vscode.workspace.onDidSaveTextDocument(doc => {
        sendDocumentSaveContext(doc);
    });
}

function connectToAgent() {
    if (ws) {
        ws.close();
    }

    statusStatusBarItem.text = '$(sync~spin) DevMind: Connecting...';
    statusStatusBarItem.show();

    // Connect to local FastAPI WebSocket port
    ws = new WebSocket('ws://localhost:7860/ws/vscode_bridge');

    ws.on('open', () => {
        statusStatusBarItem.text = '$(debug-start) DevMind: Connected';
        statusStatusBarItem.tooltip = 'Connected to local DevMind agent';
        vscode.window.showInformationMessage('Connected to DevMind Local Agent!');
        
        // Send initial context
        sendActiveEditorContext(vscode.window.activeTextEditor);
    });

    ws.on('close', () => {
        statusStatusBarItem.text = '$(debug-disconnect) DevMind: Offline';
        statusStatusBarItem.tooltip = 'DevMind agent offline. Click to reconnect.';
    });

    ws.on('error', (err) => {
        console.error('DevMind bridge error:', err);
        statusStatusBarItem.text = '$(debug-disconnect) DevMind: Offline';
    });

    ws.on('message', (message) => {
        try {
            const data = JSON.parse(message.toString());
            handleAgentMessage(data);
        } catch (e) {
            console.error('Error handling message:', e);
        }
    });
}

function handleAgentMessage(data) {
    switch (data.type) {
        case 'open_file':
            openFileInVSCode(data.path);
            break;
        
        case 'show_diff':
            showDiffInVSCode(data.path, data.original, data.modified);
            break;
            
        case 'notify':
            vscode.window.showInformationMessage(`DevMind: ${data.text}`);
            break;

        case 'error':
            vscode.window.showErrorMessage(`DevMind Error: ${data.text}`);
            break;
    }
}

async function openFileInVSCode(pathStr) {
    try {
        const uri = vscode.Uri.file(pathStr);
        const doc = await vscode.workspace.openTextDocument(uri);
        await vscode.window.showTextDocument(doc);
    } catch (e) {
        vscode.window.showErrorMessage(`Failed to open file: ${pathStr}`);
    }
}

async function showDiffInVSCode(pathStr, originalContent, modifiedContent) {
    try {
        const tempUriOrig = vscode.Uri.parse(`readonly-diff-temp:${pathStr} (Original)`);
        const tempUriMod = vscode.Uri.file(pathStr);

        // Register doc provider for original content (temp)
        const docProvider = new class {
            provideTextDocumentContent() {
                return originalContent;
            }
        };
        
        // We register doc provider if not already
        const disp = vscode.workspace.registerTextDocumentContentProvider('readonly-diff-temp', docProvider);
        
        await vscode.commands.executeCommand(
            'vscode.diff',
            tempUriOrig,
            tempUriMod,
            `Diff: ${pathStr.split(/[\\/]/).pop()}`
        );
        
        // Dispose temp registration after display
        setTimeout(() => disp.dispose(), 5000);
    } catch (e) {
        console.error('Error displaying diff:', e);
    }
}

function sendActiveEditorContext(editor) {
    if (!ws || ws.readyState !== WebSocket.OPEN || !editor) return;

    const doc = editor.document;
    const selection = editor.selection;
    const text = doc.getText(selection) || doc.getText(); // Send selected code, or entire file context

    ws.send(JSON.stringify({
        type: 'editor_context',
        path: doc.fileName,
        language: doc.languageId,
        content: text,
        selection: {
            start: selection.start,
            end: selection.end
        }
    }));
}

function sendDocumentSaveContext(doc) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    ws.send(JSON.stringify({
        type: 'document_saved',
        path: doc.fileName,
        content: doc.getText()
    }));
}

// Sidebar Webview Provider
class DevMindChatViewProvider {
    constructor(extensionUri) {
        this.extensionUri = extensionUri;
    }

    resolveWebviewView(webviewView, context, token) {
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this.extensionUri]
        };

        // Render simple iframe pointing to DevMind local UI
        webviewView.webview.html = `
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <style>
                    body, html { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; background: #0f111a; }
                    iframe { border: none; width: 100%; height: 100%; }
                </style>
            </head>
            <body>
                <iframe src="http://localhost:7860/"></iframe>
            </body>
            </html>
        `;
    }
}

function deactivate() {
    if (ws) {
        ws.close();
    }
}

module.exports = {
    activate,
    deactivate
};
