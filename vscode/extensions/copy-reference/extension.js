const path = require("path");
const vscode = require("vscode");

// Prefer workspace-relative paths so copied references are portable inside the
// current repository. Fall back to absolute paths or URIs when VSCode cannot
// resolve the document to a workspace file.
function getReferencePath(document) {
    if (document.uri.scheme !== "file") {
        return document.uri.toString();
    }

    const workspaceFolder = vscode.workspace.getWorkspaceFolder(document.uri);
    if (!workspaceFolder) {
        return document.uri.fsPath;
    }

    return path
        .relative(workspaceFolder.uri.fsPath, document.uri.fsPath)
        .split(path.sep)
        .join("/");
}

// VSCode selections are zero-based. Convert to one-based lines and avoid
// counting the next line when a multi-line selection ends at column zero.
function getSelectedLineRange(selection) {
    if (selection.isEmpty) {
        return undefined;
    }

    const startLine = selection.start.line + 1;
    let endLine = selection.end.line + 1;

    const endsAtLineStart = selection.end.character === 0;
    const spansMultipleLines = selection.end.line > selection.start.line;
    if (endsAtLineStart && spansMultipleLines) {
        endLine = selection.end.line;
    }

    return { startLine, endLine: Math.max(startLine, endLine) };
}

async function copyReference() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage(
            "No active editor to copy a reference from.",
        );
        return;
    }

    const refPath = getReferencePath(editor.document);
    const range = getSelectedLineRange(editor.selection);
    let ref = range
        ? `${refPath}:${range.startLine}:${range.endLine}`
        : refPath;

    // Prompt support is temporarily disabled. Keep the previous implementation
    // commented here so it can be re-enabled without rebuilding the command.
    // const note = await vscode.window.showInputBox({
    //     prompt: "Prompt (optional)",
    //     placeHolder: "Leave blank to copy only the reference",
    // });
    //
    // if (note === undefined) {
    //     return;
    // }
    //
    // if (note.trim()) {
    //     ref = `${ref} ${note.trim()}`;
    // }

    await vscode.env.clipboard.writeText(ref);
    vscode.window.setStatusBarMessage(`Copied: ${ref}`, 3000);
}

// Register the command contributed in package.json.
function activate(context) {
    context.subscriptions.push(
        vscode.commands.registerCommand("copyReference.copy", copyReference),
    );
}

function deactivate() {}

module.exports = {
    activate,
    deactivate,
};
