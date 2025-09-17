const vscode = require('vscode');

const zerionyxKeywords = [
    'load', 'namespace', 'done', 'defun', 'as', 'using', 'if', 'elif', 'else', 'do', 'for', 'to', 'step', 'in', 'while'
];

const zerionyxControlFlow = ['return', 'continue', 'break'];
const zerionyxOperators = ['and', 'or', 'not'];
const zerionyxConstants = ['true', 'false', 'none', 'nan', 'inf', 'neg_inf', 'is_main'];
const zerionyxTypeConstants = ['list', 'str', 'int', 'float', 'bool', 'func', 'hashmap', 'thread', 'bytes', 'cfloat', 'py_obj', 'channel_type', 'none_type', 'thread_pool_type', 'future_type'];
const zerionyxBuiltins = [
    'append', 'is_panic', 'clear', 'extend', 'input', 'get_password', 'insert', 'is_func', 'is_list', 'is_py_obj', 'is_none', 'is_num',
    'is_str', 'is_bool', 'is_thread', 'is_thread_pool', 'is_future', 'is_namespace', 'keys', 'values', 'items', 'has', 'get', 'del',
    'len', 'panic', 'pop', 'print', 'println', 'to_float', 'to_int', 'to_str', 'to_cfloat', 'to_bytes', 'type', 'pyexec', 'slice',
    'is_nan', 'is_channel', 'is_cfloat'
];

const libraryFunctions = {
    "mlist": ["map", "filter", "reduce", "min", "max", "reverse", "zip", "zip_longest", "sort", "count", "index_of", "rand_int_list", "rand_float_list"],
    "string": ["split", "strip", "join", "replace", "to_upper", "to_lower", "ord", "chr", "is_digit", "is_ascii_lowercase", "is_ascii_uppercase", "is_ascii_letter", "is_space", "find", "find_all", "startswith", "endswith", "encode", "decode"],
    "math": ["sqrt", "abs", "fact", "sin", "cos", "tan", "gcd", "lcm", "fib", "is_prime", "deg2rad", "rad2deg", "exp", "log", "sinh", "cosh", "tanh", "round", "is_close"],
    "ffio": ["write", "read", "exists", "get_cdir", "set_cdir", "list_dir", "make_dir", "remove_file", "rename", "remove_dir", "copy", "is_file", "abs_path", "base_name", "dir_name", "symlink", "readlink", "stat", "lstat", "walk", "chmod", "chown", "utime", "link", "unlink", "access", "path_join", "is_dir", "is_link", "is_mount"],
    "hash": ["md5", "sha1", "sha256", "sha512", "crc32"],
    "memory": ["remember", "recall", "forget", "clear_memory", "keys", "is_empty", "size"],
    "net": ["get_ip", "get_mac", "ping", "downl", "get_local_ip", "get_hostname", "request"],
    "random": ["rand", "rand_int", "rand_float", "rand_choice", "int_seed", "float_seed"],
    "sys": ["system", "osystem", "get_env", "set_env", "exit"],
    "threading": ["start", "sleep", "join", "is_alive", "cancel"],
    "threading.pool": ["new", "submit", "shutdown", "result", "is_done"],
    "time": ["sleep", "time", "ctime"],
    "keyboard": ["write", "press", "release", "wait", "is_pressed"],
    "termcolor": ["cprint", "cprintln", "get_code"],
    "mouse": ["move", "click", "right_click", "scroll", "position"],
    "screen": ["capture", "capture_area", "get_color"],
    "json": ["parse", "stringify"],
    "decorators": ["cache", "once", "retry", "timeout", "log_call", "measure_time", "repeat", "ignore_error", "deprecated", "lazy"],
    "channel": ["new", "send", "recv", "is_empty"]
};

const libraryConstants = {
    "math": ["PI", "E", "ln2"],
    "ffio": ["os_sep"],
    "sys": ["argv", "os_name"]
};

function activate(context) {
    const provider = vscode.languages.registerCompletionItemProvider('zerionyx', {
        provideCompletionItems(document, position) {
            const linePrefix = document.lineAt(position).text.slice(0, position.character);
            const fullText = document.getText();

            for (const lib in libraryFunctions) {
                if (linePrefix.endsWith(`${lib}.`)) {
                    const funcs = libraryFunctions[lib].map(func => new vscode.CompletionItem(func, vscode.CompletionItemKind.Method));
                    const consts = (libraryConstants[lib] || []).map(c => new vscode.CompletionItem(c, vscode.CompletionItemKind.Field));
                    return [...funcs, ...consts];
                }
            }

            const userDefinedCompletions = [];
            const variableRegex = /([a-zA-Z_]\w*)\s*=/g;
            const asVariableRegex = /(?<=\bas\b\s+)([a-zA-Z_]\w*)/g;
            const functionRegex = /defun\s+([a-zA-Z_]\w*)/g;
            const namespaceRegex = /namespace\s+([a-zA-Z_]\w*)/g;
            const forInVarRegex = /\bfor\s+([a-zA-Z_]\w*)\s+in\b/g;
            const forToVarRegex = /\bfor\s+([a-zA-Z_]\w*)\s*=/g;

            let match;
            while ((match = variableRegex.exec(fullText)) !== null) {
                userDefinedCompletions.push(new vscode.CompletionItem(match[1], vscode.CompletionItemKind.Variable));
            }
            while ((match = asVariableRegex.exec(fullText)) !== null) {
                userDefinedCompletions.push(new vscode.CompletionItem(match[1], vscode.CompletionItemKind.Variable));
            }
            while ((match = functionRegex.exec(fullText)) !== null) {
                userDefinedCompletions.push(new vscode.CompletionItem(match[1], vscode.CompletionItemKind.Function));
            }
            while ((match = namespaceRegex.exec(fullText)) !== null) {
                userDefinedCompletions.push(new vscode.CompletionItem(match[1], vscode.CompletionItemKind.Module));
            }
            while ((match = forInVarRegex.exec(fullText)) !== null) {
                userDefinedCompletions.push(new vscode.CompletionItem(match[1], vscode.CompletionItemKind.Variable));
            }
            while ((match = forToVarRegex.exec(fullText)) !== null) {
                userDefinedCompletions.push(new vscode.CompletionItem(match[1], vscode.CompletionItemKind.Variable));
            }

            const allKeywords = [
                ...zerionyxKeywords.map(k => new vscode.CompletionItem(k, vscode.CompletionItemKind.Keyword)),
                ...zerionyxControlFlow.map(k => new vscode.CompletionItem(k, vscode.CompletionItemKind.Keyword)),
                ...zerionyxOperators.map(k => new vscode.CompletionItem(k, vscode.CompletionItemKind.Operator)),
                ...zerionyxConstants.map(k => new vscode.CompletionItem(k, vscode.CompletionItemKind.Constant)),
                ...zerionyxTypeConstants.map(k => new vscode.CompletionItem(k, vscode.CompletionItemKind.TypeParameter)),
                ...zerionyxBuiltins.map(k => new vscode.CompletionItem(k, vscode.CompletionItemKind.Function)),
            ];

            const allCompletions = [...allKeywords, ...userDefinedCompletions];

            const uniqueCompletions = Array.from(new Set(allCompletions.map(item => item.label)))
                .map(label => {
                    return allCompletions.find(item => item.label === label);
                });

            return uniqueCompletions;
        }
    }, '.');

    context.subscriptions.push(provider);
}

module.exports = {
    activate
};
// TODO: cập nhật tự hoàn thành cú pháp và tô màu