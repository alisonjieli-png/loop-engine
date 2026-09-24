"""Per-program readers of the command risk policy.

Each reader names the effects of one program family (git, the code host,
cloud command lines, HTTP clients, package managers, containers, databases,
shells and interpreters) from its arguments, without running anything. The
parse, the wrapper handling and the policy's public contract live in
``command_risk_policy``; this module is its program table.

Owns: read_program and the program vocabularies. Does not own the effect
vocabulary, the grant rule or the assessment record.
"""
from __future__ import annotations

import re

from .command_risk_policy import (
    DELETE, EXECUTE, HISTORY_REWRITE, NETWORK, PRIVILEGE, PROCESS_CONTROL, PUBLISH, READ, SYSTEM, WRITE,
    _SYSTEM_PATH, _Context, _Findings, _assess_simple, _assess_text,
)
_SHELLS = frozenset({"sh", "bash", "zsh", "dash", "ksh", "fish", "busybox"})
_INTERPRETERS = frozenset({"python", "python2", "python3", "node", "perl", "ruby", "php", "deno", "pypy",
                           "pypy3"})
_READ_ONLY = frozenset({
    "ls", "cat", "head", "tail", "less", "more", "grep", "egrep", "fgrep", "rg", "ag", "wc", "sort",
    "uniq", "cut", "tr", "diff", "cmp", "file", "stat", "du", "df", "ps", "top", "htop", "pwd", "echo",
    "printf", "true", "false", "test", "[", "[[", "]]", "which", "whereis", "type", "date", "printenv",
    "id", "whoami", "uname", "hostname", "basename", "dirname", "realpath", "readlink", "sha256sum",
    "sha1sum", "md5sum", "cksum", "b2sum", "jq", "yq", "xxd", "od", "hexdump", "strings", "tree",
    "column", "nl", "fold", "fmt", "comm", "join", "paste", "sleep", "wait", "seq", "yes", "expr", "bc",
    "lsof", "free", "uptime", "nproc", "lscpu", "nvidia-smi", "locate", "cd", "pushd", "popd", "set",
    "export", "unset", "read", "shift", "local", "declare", "typeset", "alias", "unalias", "history",
    "man", "help", "info", "fi", "done", "esac", "case", "for", "in", "select", "function", "return",
    "break", "continue", "exit", "trap", "getconf", "tput", "stty", "clear", "zcat", "bzcat", "xzcat",
    "base64", "sum", "tac", "rev", "shuf", "look", "cal", "w", "last", "who", "pgrep", "pidof", "ss",
    "netstat", "lsblk", "blkid", "findmnt", "getent", "ldd", "nm", "objdump", "readelf", ":", "umask",
    "hash", "jobs", "fg", "bg", "disown", "ulimit", "times", "dirs", "let", "sha512sum", "numfmt",
    "iconv", "envsubst", "diff3", "sdiff", "tsort", "ptx", "csplit", "split", "expand", "unexpand",
})
_WRITE_ALL_ARGUMENTS = frozenset({"mkdir", "touch", "tee", "mktemp", "mkfifo"})
_WRITE_LAST_ARGUMENT = frozenset({"ln", "install", "patch"})
_ARCHIVERS = frozenset({"zip", "unzip", "gzip", "bzip2", "xz", "7z", "gunzip", "unxz", "bunzip2", "zstd",
                        "unzstd"})
_DELETE_PROGRAMS = frozenset({"rm", "rmdir", "unlink", "shred", "srm", "wipe"})
_NETWORK_PROGRAMS = frozenset({
    "nc", "ncat", "netcat", "telnet", "ftp", "ping", "dig", "nslookup", "host", "traceroute", "mosh",
    "aria2c", "lynx", "w3m", "opencode", "codex", "claude", "gemini", "aider", "huggingface-cli", "hf",
    "ollama", "npx", "pnpx", "bunx", "uvx", "pipx", "apt", "apt-get", "brew", "dnf", "yum", "snap",
    "pacman", "apk", "port", "choco", "winget", "sendmail", "mail", "mailx", "mutt", "msmtp", "swaks",
    "twine"})
_PROCESS_PROGRAMS = frozenset({"kill", "pkill", "killall", "systemctl", "service", "launchctl", "crontab",
                               "renice", "at", "batch"})
_SYSTEM_PROGRAMS = frozenset({
    "mkfs", "fdisk", "parted", "sfdisk", "gdisk", "wipefs", "mkswap", "swapon", "swapoff", "umount",
    "modprobe", "rmmod", "insmod", "sysctl", "iptables", "ip6tables", "nft", "ufw", "firewall-cmd",
    "reboot", "shutdown", "halt", "poweroff", "init", "telinit", "visudo", "passwd", "useradd", "userdel",
    "usermod", "groupadd", "groupdel", "setcap", "chattr", "update-grub", "grub-install", "efibootmgr",
    "cryptsetup", "lvremove", "vgremove", "pvremove", "zpool", "zfs", "btrfs", "losetup", "chroot"})
_DELETE_CALLS = re.compile(r"(?:shutil\.rmtree|os\.(?:remove|unlink|rmdir|removedirs)|\.unlink\(|\.rmdir\(|"
                           r"rmSync|unlinkSync|rmdirSync|fs\.rm\b|fs\.promises\.rm\b|FileUtils\.rm|"
                           r"\bunlink\s*\(|\brmtree\b|File\.delete|os\.system\(\s*['\"]rm\b)")
_NETWORK_CALLS = re.compile(r"(?:\brequests\.|\burllib|http\.client|\bhttpx\b|\bsocket\.|\burlopen|aiohttp|"
                            r"\bfetch\(|\baxios|XMLHttpRequest|Net::HTTP|LWP::|smtplib|ftplib|paramiko|"
                            r"https?://)")
_PROCESS_CALLS = re.compile(r"(?:\bsubprocess\b|os\.system|os\.popen|os\.exec|ch[i]ld_process|\bexecSync\b|"
                            r"\bspawn\(|\bsystem\(|\bexec\(|`)")
_FILE_WRITE_CALLS = re.compile(r"(?:open\([^)]*['\"][wax]b?\+?['\"]|write_text|write_bytes|\.write\(|"
                               r"writeFile|appendFile|shutil\.(?:copy|move)|os\.(?:rename|replace))")
_SQL_DESTRUCTIVE = re.compile(r"\b(?:drop\s+(?:table|database|schema|index|view|user|role)|delete\s+from|"
                              r"truncate\s+(?:table\s+)?\w|alter\s+table\s+\S+\s+drop)\b", re.IGNORECASE)
_SQL_WRITE = re.compile(r"\b(?:insert\s+into|update\s+\S+\s+set|create\s+(?:table|index|view|database)|"
                        r"alter\s+table|grant|revoke)\b", re.IGNORECASE)
_URL = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
_REMOTE_PATH = re.compile(r"^(?:[\w.-]+@[\w.-]+:|[\w-]+(?:\.[\w-]+)+:/)")


def read_program(program, args, findings, context, depth, heredoc):
    """Name the effects of one resolved program and its arguments."""
    handler = _HANDLERS.get(program)
    if handler is not None:
        handler(program, args, findings, context, depth, heredoc)
    elif program in _SHELLS:
        _shell(program, args, findings, context, depth, heredoc)
    elif program in _INTERPRETERS:
        _interpreter(program, args, findings, context, depth, heredoc)
    elif program in _DELETE_PROGRAMS:
        _delete(program, args, findings, context)
    elif program in _NETWORK_PROGRAMS:
        _network_program(program, args, findings)
    elif program in _PROCESS_PROGRAMS:
        _process(program, args, findings)
    elif program in _SYSTEM_PROGRAMS:
        findings.add(SYSTEM, f"{program} changes the machine itself", irreversible=True)
    elif program in ("eval", "source", "."):
        if program == "eval":
            findings.blind("eval runs a computed command")
        else:
            findings.add(EXECUTE, f"{program} runs a script in the current shell")
    elif program in _WRITE_ALL_ARGUMENTS or program in _WRITE_LAST_ARGUMENT:
        findings.add(WRITE, f"{program} writes files")
        targets = _targets(args)
        written = targets if program in _WRITE_ALL_ARGUMENTS else targets[-1:]
        if any(_SYSTEM_PATH.match(target) for target in written):
            findings.add(SYSTEM, f"{program} writes a system path", irreversible=True)
    elif program in _ARCHIVERS:
        findings.add(WRITE, f"{program} writes archive files")
    elif program in _READ_ONLY:
        findings.add(READ, f"{program} reads")
    else:
        # An unknown program or a project script. Its own effects are not
        # inspected, the way a step runs its project's code in its workspace.
        findings.add(EXECUTE, f"{program} runs code whose effects are not inspected")
    if program not in _READ_ONLY and any(_URL.match(arg) or _REMOTE_PATH.match(arg)
                                         for arg in _targets(args)):
        findings.add(NETWORK, "an argument names a remote address")


def _targets(args):
    return [arg for arg in args if not arg.startswith("-")]


def _delete(program, args, findings, context):
    irreversible = not context.reversible_deletes or program in ("shred", "srm", "wipe")
    findings.add(DELETE, f"{program} deletes files", irreversible=irreversible)
    for target in _targets(args):
        if _SYSTEM_PATH.match(target):
            findings.add(SYSTEM, f"{program} deletes a system or home path", irreversible=True)


def _mv(program, args, findings, context, depth, heredoc):
    targets = _targets(args)
    if targets and targets[-1] == "/dev/null":
        findings.add(DELETE, "mv into /dev/null deletes", irreversible=not context.reversible_deletes)
    elif any(_SYSTEM_PATH.match(target) for target in targets):
        findings.add(SYSTEM, "mv touches a system path", irreversible=True)
    else:
        findings.add(WRITE, "mv moves files")


def _cp(program, args, findings, context, depth, heredoc):
    targets = _targets(args)
    if targets[:1] == ["/dev/null"]:
        findings.add(DELETE, "copying /dev/null over a file empties it", irreversible=not context.reversible_deletes)
    if targets and _SYSTEM_PATH.match(targets[-1]):
        findings.add(SYSTEM, "cp writes a system path", irreversible=True)
    else:
        findings.add(WRITE, "cp copies files")


def _find(program, args, findings, context, depth, heredoc):
    findings.add(READ, "find reads the file tree")
    if "-delete" in args:
        findings.add(DELETE, "find -delete deletes what it matches", irreversible=not context.reversible_deletes)
    for flag in ("-fprint", "-fprintf", "-fls", "-fprint0"):
        if flag in args:
            findings.add(WRITE, f"find {flag} writes a file")
    rest = list(args)
    for flag in ("-exec", "-execdir", "-ok", "-okdir"):
        while flag in rest:
            start = rest.index(flag) + 1
            end = next((i for i in range(start, len(rest)) if rest[i] in (";", "+", "\\;")), len(rest))
            _assess_simple(rest[start:end], [], findings, context, depth + 1)
            rest = rest[:start - 1] + rest[end + 1:]


def _xargs(program, args, findings, context, depth, heredoc):
    takes_value = {"-I", "-i", "-n", "-P", "-L", "-l", "-s", "-d", "-E", "-e", "-a", "--max-args",
                   "--max-procs", "--max-lines", "--delimiter", "--arg-file", "--replace", "-j", "--jobs",
                   "-S", "--process-slot-var"}
    index = 0
    while index < len(args) and args[index].startswith("-"):
        index += 2 if args[index] in takes_value else 1
    if index < len(args):
        _assess_simple(args[index:], [], findings, context, depth + 1)
    else:
        findings.add(READ, f"{program} with no command echoes its input")


def _sed(program, args, findings, context, depth, heredoc):
    if any(arg == "--in-place" or arg.startswith("--in-place=") or re.fullmatch(r"-[a-zA-Z]*i\S*", arg)
           for arg in args):
        findings.add(WRITE, "sed -i edits files in place")
    else:
        findings.add(READ, "sed reads")
    if any(re.search(r"(?:^|;)\s*[0-9,$]*\s*[ew]\s", arg) or re.search(r"/[ew]\s*$", arg)
           for arg in args if not arg.startswith("-")):
        findings.blind("a sed script runs or writes through its own commands")


def _awk(program, args, findings, context, depth, heredoc):
    script = " ".join(args)
    if "system(" in script or re.search(r'\|\s*"', script) or "getline" in script and '"' in script:
        findings.blind("awk runs a computed command")
    elif re.search(r'print[^;]*>\s*"', script):
        findings.add(WRITE, "awk writes a file")
    else:
        findings.add(READ, "awk reads")


def _truncate(program, args, findings, context, depth, heredoc):
    findings.add(DELETE, "truncate discards file contents", irreversible=not context.reversible_deletes)


def _dd(program, args, findings, context, depth, heredoc):
    target = next((arg[3:] for arg in args if arg.startswith("of=")), "")
    if target.startswith("/dev/") or (target and _SYSTEM_PATH.match(target)):
        findings.add(SYSTEM, "dd writes a device or system path", irreversible=True)
    elif target:
        findings.add(WRITE, "dd writes a file")
    else:
        findings.add(READ, "dd copies to standard output")


def _chmod(program, args, findings, context, depth, heredoc):
    targets = _targets(args)[1:]
    if any(_SYSTEM_PATH.match(target) for target in targets):
        findings.add(SYSTEM, f"{program} changes a system path", irreversible=True)
    elif program in ("chown", "chgrp"):
        findings.add(PRIVILEGE, f"{program} changes ownership")
    else:
        findings.add(WRITE, "chmod changes file modes")


def _tar(program, args, findings, context, depth, heredoc):
    findings.add(WRITE, "tar writes an archive or its files")
    if "--remove-files" in args:
        findings.add(DELETE, "tar --remove-files deletes the archived files",
                     irreversible=not context.reversible_deletes)
    for index, arg in enumerate(args):
        target = args[index + 1] if arg in ("-C", "--directory") and index + 1 < len(args) else ""
        if target and _SYSTEM_PATH.match(target):
            findings.add(SYSTEM, "tar extracts into a system path", irreversible=True)


def _rsync(program, args, findings, context, depth, heredoc):
    findings.add(WRITE, "rsync copies files")
    if any(_URL.match(arg) or re.match(r"^(?:[\w.-]+@)?[\w.-]+:", arg) for arg in _targets(args)):
        findings.add(NETWORK, "rsync reaches a remote host")
    if any(arg.startswith("--delete") or arg == "--remove-source-files" for arg in args):
        findings.add(DELETE, "rsync deletes files at the destination or source",
                     irreversible=not context.reversible_deletes)


def _database(program, args, findings, context, depth, heredoc):
    statement = " ".join(args) + "\n" + heredoc
    if _SQL_DESTRUCTIVE.search(statement):
        findings.add(DELETE, f"{program} runs a destructive database statement", irreversible=True)
    elif _SQL_WRITE.search(statement):
        findings.add(WRITE, f"{program} changes a database")
    else:
        findings.add(READ, f"{program} reads a database")
    if program != "sqlite3" and (any(arg in ("-h", "--host") or arg.startswith("--host=") for arg in args)
                                 or any(_URL.match(arg) for arg in args)):
        findings.add(NETWORK, f"{program} reaches a database server")


def _docker(program, args, findings, context, depth, heredoc):
    words = _targets(args)
    verb = words[0] if words else ""
    sub = words[1] if len(words) > 1 else ""
    if verb in ("rm", "rmi", "prune") or (verb in ("volume", "image", "container", "network", "builder",
                                                    "system") and sub in ("rm", "prune", "remove")):
        findings.add(DELETE, f"{program} {verb} deletes containers, images or volumes", irreversible=True)
    elif verb in ("push", "login"):
        findings.add(PUBLISH, f"{program} {verb} publishes to a registry", irreversible=True)
        findings.add(NETWORK, f"{program} reaches a registry")
    elif verb in ("pull", "build", "search"):
        findings.add(NETWORK, f"{program} {verb} reaches a registry")
    elif verb in ("stop", "kill", "restart", "pause"):
        findings.add(PROCESS_CONTROL, f"{program} {verb} controls running containers")
    elif verb in ("run", "exec", "compose", "start", "create", "up"):
        findings.add(EXECUTE, f"{program} {verb} runs a container")
        if verb == "exec" and len(words) > 2:
            _assess_simple(words[2:], [], findings, context, depth + 1)
    else:
        findings.add(READ, f"{program} reads its state")


def _kubectl(program, args, findings, context, depth, heredoc):
    findings.add(NETWORK, "kubectl reaches a cluster")
    verb = next((arg for arg in args if not arg.startswith("-")), "")
    if verb in ("delete", "drain"):
        findings.add(DELETE, f"kubectl {verb} removes cluster resources", irreversible=True)
    elif verb in ("apply", "create", "patch", "replace", "scale", "rollout", "set", "edit", "label",
                  "annotate", "cordon", "taint", "exec", "cp", "run", "expose", "autoscale"):
        findings.add(PUBLISH, f"kubectl {verb} changes a live cluster", irreversible=True)


_DOWNLOADING_VERBS = frozenset({"install", "i", "add", "ci", "update", "upgrade", "download", "fetch", "get",
                                "sync", "remove", "uninstall", "rm", "audit", "outdated", "init", "create",
                                "dlx", "exec", "x", "build", "lock", "restore"})
_PUBLISHING_VERBS = frozenset({"publish", "unpublish", "deprecate", "owner", "dist-tag", "login", "adduser",
                               "yank", "upload", "release"})


def _package_manager(program, args, findings, context, depth, heredoc):
    verb = next((arg for arg in args if not arg.startswith("-")), "")
    if verb in _PUBLISHING_VERBS:
        findings.add(PUBLISH, f"{program} {verb} publishes to a registry", irreversible=True)
        findings.add(NETWORK, f"{program} reaches a registry")
    elif (program == "go" and verb in ("get", "install", "mod")) or (
            program != "go" and verb in _DOWNLOADING_VERBS):
        findings.add(NETWORK, f"{program} {verb} downloads packages")
        findings.add(WRITE, f"{program} {verb} changes installed packages")
    else:
        findings.add(EXECUTE, f"{program} runs project code")


def _pip(program, args, findings, context, depth, heredoc):
    verb = next((arg for arg in args if not arg.startswith("-")), "")
    if verb in ("install", "download", "wheel", "index", "search"):
        findings.add(NETWORK, f"{program} {verb} downloads packages")
        findings.add(WRITE, f"{program} {verb} changes installed packages")
    elif verb == "uninstall":
        findings.add(WRITE, f"{program} uninstall removes installed packages")
    else:
        findings.add(READ, f"{program} {verb} reads package state".replace("  ", " "))


def _uv(program, args, findings, context, depth, heredoc):
    verb = next((arg for arg in args if not arg.startswith("-")), "")
    if verb == "pip":
        _pip("uv pip", args[args.index("pip") + 1:], findings, context, depth, heredoc)
    elif verb == "publish":
        findings.add(PUBLISH, "uv publish uploads a package", irreversible=True)
        findings.add(NETWORK, "uv reaches a registry")
    elif verb in ("add", "sync", "lock", "venv", "tool", "python", "run", "init", "remove", "export"):
        findings.add(NETWORK, f"uv {verb} may download packages")
        findings.add(WRITE, f"uv {verb} changes the environment")
    else:
        findings.add(READ, f"uv {verb} reads".replace("  ", " "))


_GIT_READING = frozenset({
    "status", "log", "diff", "show", "blame", "grep", "ls-files", "ls-tree", "rev-parse", "describe",
    "shortlog", "cat-file", "rev-list", "merge-base", "name-rev", "for-each-ref", "show-ref",
    "count-objects", "fsck", "whatchanged", "var", "help", "version", "check-ignore", "cherry", "range-diff",
    "reflog", "config", "notes", "", "bisect", "check-attr", "show-branch", "annotate", "difftool"})
_GIT_REMOTE = frozenset({"fetch", "pull", "clone", "ls-remote", "remote", "submodule", "lfs", "archive"})


def _git(program, args, findings, context, depth, heredoc):
    index = 0
    while index < len(args) and args[index].startswith("-"):
        if args[index] == "-c" and index + 1 < len(args):
            if args[index + 1].lower().startswith("alias."):
                findings.blind("git -c alias defines a computed git command")
            index += 2
            continue
        index += 2 if args[index] in ("-C", "--git-dir", "--work-tree", "--namespace") else 1
    verb = args[index] if index < len(args) else ""
    rest = args[index + 1:]
    options = [arg for arg in rest if arg.startswith("-")]
    positional = [arg for arg in rest if not arg.startswith("-")]
    if verb in _GIT_READING:
        if verb == "reflog" and positional[:1] in (["expire"], ["delete"]):
            findings.add(HISTORY_REWRITE, "git reflog expire discards recovery points", irreversible=True)
        elif verb == "config" and len(positional) > 1 and not any(
                option in ("--get", "--list", "-l", "--get-all", "--get-regexp") for option in options):
            findings.add(WRITE, "git config writes a setting")
        elif verb == "bisect" and positional[:1] not in ([], ["log"], ["view"], ["visualize"]):
            findings.add(WRITE, "git bisect moves the working tree")
        elif verb == "notes" and positional[:1] in (["add"], ["remove"], ["prune"], ["edit"], ["append"]):
            findings.add(WRITE, "git notes changes notes")
        else:
            findings.add(READ, f"git {verb or 'command'} reads the repository")
        return
    if verb in _GIT_REMOTE:
        if verb == "remote":
            if positional[:1] in (["remove"], ["rm"], ["set-url"], ["add"], ["rename"], ["prune"]):
                findings.add(WRITE, "git remote changes the configured remotes")
                return
            if positional[:1] != ["update"]:
                findings.add(READ, "git remote reads the configured remotes")
                return
        findings.add(NETWORK, f"git {verb} reaches a remote")
        findings.add(WRITE, f"git {verb} writes the local repository")
        if verb == "pull" and ("--rebase" in options or "-r" in options):
            findings.add(HISTORY_REWRITE, "git pull --rebase rewrites local commits")
        return
    if verb == "push":
        findings.add(NETWORK, "git push reaches a remote")
        findings.add(PUBLISH, "git push publishes commits", irreversible=True)
        if any(option in ("-f", "--force", "--force-with-lease", "--force-if-includes", "--mirror", "--prune")
               or option.startswith("--force-with-lease=") for option in options) \
                or any(arg.startswith("+") for arg in positional):
            findings.add(HISTORY_REWRITE, "git push --force rewrites published history", irreversible=True)
        if "--delete" in options or "-d" in options or any(arg.startswith(":") for arg in positional):
            findings.add(DELETE, "git push deletes a remote reference", irreversible=True)
        return
    if verb == "reset":
        if any(option in ("--hard", "--merge", "--keep") for option in options):
            findings.add(HISTORY_REWRITE, "git reset --hard discards uncommitted work", irreversible=True)
            findings.add(DELETE, "git reset --hard deletes working changes", irreversible=True)
        elif positional and positional[0] != "--" and re.fullmatch(
                r"(?:HEAD|@)(?:[~^]\d*)+|[0-9a-f]{7,40}|origin/\S+|FETCH_HEAD|ORIG_HEAD", positional[0]):
            findings.add(HISTORY_REWRITE, "git reset moves the branch to another commit")
        else:
            findings.add(WRITE, "git reset changes the index")
        return
    if verb in ("rebase", "filter-branch", "filter-repo", "replace", "update-ref"):
        irreversible = verb in ("filter-branch", "filter-repo") or (verb == "update-ref" and "-d" in options)
        findings.add(HISTORY_REWRITE, f"git {verb} rewrites history", irreversible=irreversible)
        return
    if verb == "commit":
        if "--amend" in options:
            findings.add(HISTORY_REWRITE, "git commit --amend rewrites the last commit")
        else:
            findings.add(WRITE, "git commit records a commit")
        return
    if verb == "clean":
        if "--dry-run" in options or any(re.fullmatch(r"-[a-zA-Z]*n[a-zA-Z]*", option) for option in options):
            findings.add(READ, "git clean -n only lists what it would delete")
        else:
            findings.add(DELETE, "git clean deletes untracked files", irreversible=True)
        return
    if verb in ("checkout", "restore", "switch"):
        branch_making = any(option in ("-b", "-B", "-c", "-C", "--orphan") for option in options)
        discards = not branch_making and (
            "--" in rest or "." in positional or any(option in ("-f", "--force", "--discard-changes")
                                                     for option in options)
            or (verb == "restore" and not ("--staged" in options and "--worktree" not in options)))
        if discards:
            findings.add(DELETE, f"git {verb} discards uncommitted changes", irreversible=True)
        else:
            findings.add(WRITE, f"git {verb} switches the working tree")
        return
    if verb == "stash":
        if positional[:1] in (["drop"], ["clear"]):
            findings.add(DELETE, "git stash drop discards stashed work", irreversible=True)
        else:
            findings.add(WRITE, "git stash stores working changes")
        return
    if verb in ("branch", "tag", "worktree"):
        if any(option in ("-D", "-d", "--delete") for option in options) or (
                verb == "worktree" and positional[:1] in (["remove"], ["prune"])):
            findings.add(DELETE, f"git {verb} deletes a reference or worktree",
                         irreversible=verb == "worktree" or "-D" in options or not context.reversible_deletes)
        elif any(option in ("-f", "--force", "-M", "-C") for option in options):
            findings.add(HISTORY_REWRITE, f"git {verb} --force moves an existing reference")
        else:
            findings.add(WRITE, f"git {verb} writes a reference")
        return
    if verb == "gc":
        if any(option.startswith("--prune") for option in options) or "--aggressive" in options:
            findings.add(HISTORY_REWRITE, "git gc --prune discards unreachable commits", irreversible=True)
        else:
            findings.add(WRITE, "git gc packs the repository")
        return
    if verb == "rm":
        cached = "--cached" in options
        findings.add(DELETE, "git rm removes files" + (" from the index" if cached else ""),
                     irreversible=not cached and not context.reversible_deletes)
        return
    if verb == "send-email":
        findings.add(PUBLISH, "git send-email sends email", irreversible=True)
        findings.add(NETWORK, "git send-email reaches a mail server")
        return
    findings.add(WRITE, f"git {verb} changes the local repository")


_DELETING_ACTIONS = frozenset({"delete", "archive"})
_LOCAL_ACTIONS = frozenset({"clone", "checkout"})
_CHANGING_ACTIONS = frozenset({
    "create", "merge", "close", "edit", "comment", "review", "reopen", "upload", "rerun", "cancel", "run",
    "transfer", "rename", "sync", "fork", "lock", "pin", "ready", "set", "add", "remove", "enable", "disable",
    "develop", "deploy", "unarchive", "login", "logout", "secret", "variable", "dispatch", "approve", "mark",
    "unlock", "unpin", "revert", "trigger"})


def _gh(program, args, findings, context, depth, heredoc):
    findings.add(NETWORK, f"{program} reaches the code host")
    words = _targets(args)
    group, action = (words + ["", ""])[:2]
    if group == "api":
        method = next((args[i + 1] for i, arg in enumerate(args[:-1]) if arg in ("-X", "--method")), "GET")
        if method.upper() != "GET" or any(arg in ("-f", "-F", "--field", "--raw-field", "--input")
                                          for arg in args):
            findings.add(PUBLISH, f"{program} api sends a changing request", irreversible=True)
        return
    if action in _DELETING_ACTIONS:
        findings.add(DELETE, f"{program} {group} {action} deletes on the code host", irreversible=True)
    elif action in _LOCAL_ACTIONS:
        findings.add(WRITE, f"{program} {group} {action} writes the local repository")
    elif action in _CHANGING_ACTIONS or group in ("secret", "variable"):
        findings.add(PUBLISH, f"{program} {group} {action} changes the code host", irreversible=True)


_DESTRUCTIVE_WORDS = frozenset({"destroy", "delete", "rm", "rb", "remove", "terminate", "purge", "unset",
                                "revoke", "drop", "wipe", "prune", "rollback"})
_CHANGING_WORDS = frozenset({
    "deploy", "apply", "create", "update", "set", "put", "cp", "mv", "sync", "restart", "scale", "launch",
    "import", "attach", "detach", "start", "stop", "suspend", "resume", "move", "release", "promote",
    "allocate", "invoke", "publish", "upload", "send", "extend", "fork", "clone", "migrate", "exec", "ssh",
    "console", "post", "login", "up", "push", "mount", "disable", "enable", "install", "upgrade", "trigger",
    "add", "rotate", "grant", "cordon", "uncordon", "kill", "cancel", "refund", "capture"})


def _cloud(program, args, findings, context, depth, heredoc):
    findings.add(NETWORK, f"{program} reaches a provider")
    words = {arg.lower() for arg in args if not arg.startswith("-")}
    destructive = sorted(_DESTRUCTIVE_WORDS & words)
    if destructive:
        findings.add(DELETE, f"{program} {' '.join(destructive)} removes provider resources", irreversible=True)
    elif _CHANGING_WORDS & words:
        findings.add(PUBLISH, f"{program} changes live provider state", irreversible=True)


def _http_client(program, args, findings, context, depth, heredoc):
    findings.add(NETWORK, f"{program} reaches a remote address")
    method = ""
    for index, arg in enumerate(args):
        if arg in ("-X", "--request", "--method") and index + 1 < len(args):
            method = args[index + 1].upper()
        elif re.fullmatch(r"-X\w+", arg):
            method = arg[2:].upper()
        elif arg.startswith(("--request=", "--method=")):
            method = arg.split("=", 1)[1].upper()
        elif program in ("http", "https", "xh") and arg.upper() in ("POST", "PUT", "PATCH", "DELETE"):
            method = arg.upper()
    sends = any(arg in ("-d", "--data", "--data-raw", "--data-binary", "--data-urlencode", "-F", "--form",
                        "-T", "--upload-file", "--json", "--post-data", "--post-file", "--body-data",
                        "--body-file")
                or (arg.startswith(("--data", "--json", "--form", "--post-", "--upload-file"))
                    and "=" in arg) for arg in args)
    if method in ("POST", "PUT", "PATCH", "DELETE") or sends:
        findings.add(PUBLISH, f"{program} sends a changing request", irreversible=True)
        if method == "DELETE":
            findings.add(DELETE, f"{program} sends a DELETE request", irreversible=True)
    if program == "wget" or any(arg in ("-o", "-O", "--output", "--remote-name", "-P", "--directory-prefix",
                                        "--output-document", "--remote-name-all")
                                or arg.startswith(("--output=", "--output-document=")) for arg in args):
        findings.add(WRITE, f"{program} saves a download")


def _network_program(program, args, findings):
    findings.add(NETWORK, f"{program} reaches a remote address")
    if program in ("sendmail", "mail", "mailx", "mutt", "msmtp", "swaks", "twine"):
        findings.add(PUBLISH, f"{program} sends or publishes outside the workspace", irreversible=True)
    elif program in ("opencode", "codex", "claude", "gemini", "aider", "ollama", "huggingface-cli", "hf",
                     "npx", "pnpx", "bunx", "uvx"):
        findings.add(EXECUTE, f"{program} runs an agent, a model session or downloaded code")
    elif program in ("apt", "apt-get", "brew", "dnf", "yum", "snap", "pacman", "apk", "port", "choco",
                     "winget", "pipx"):
        findings.add(SYSTEM, f"{program} changes installed system software")


def _ssh(program, args, findings, context, depth, heredoc):
    findings.add(NETWORK, f"{program} reaches a remote host")
    if program in ("scp", "sftp"):
        findings.add(WRITE, f"{program} copies files")
        return
    takes_value = {"-p", "-i", "-l", "-o", "-F", "-J", "-L", "-R", "-D", "-W", "-b", "-c", "-E", "-m", "-O",
                   "-Q", "-S", "-w", "-e", "-B", "-I"}
    words, index = [], 0
    while index < len(args):
        if args[index].startswith("-") and not words:
            index += 2 if args[index] in takes_value else 1
            continue
        words.append(args[index])
        index += 1
    if len(words) > 1:
        remote = _Findings()
        _assess_text(" ".join(words[1:]), remote, _Context(False), depth + 1)
        for effect in sorted(remote.effects):
            findings.add(effect, "the remote command: " + (remote.reasons[0] if remote.reasons else effect),
                         irreversible=remote.irreversible)
        if remote.effects - {READ}:
            findings.add(PUBLISH, "ssh runs a changing command on another machine", irreversible=True)
        findings.complete = findings.complete and remote.complete
    else:
        findings.add(EXECUTE, "ssh opens a remote session")
    if heredoc:
        findings.blind("ssh runs commands read from its input on another machine")


def _process(program, args, findings):
    if program == "crontab":
        if "-r" in args:
            findings.add(DELETE, "crontab -r removes the schedule", irreversible=True)
        elif "-l" in args:
            findings.add(READ, "crontab -l reads the schedule")
        else:
            findings.add(PROCESS_CONTROL, "crontab changes scheduled commands")
        return
    if program in ("systemctl", "service", "launchctl"):
        verbs = {arg for arg in args if not arg.startswith("-")}
        if verbs and verbs <= {"status", "is-active", "is-enabled", "list-units", "list-unit-files", "show",
                               "cat", "list", "print"}:
            findings.add(READ, f"{program} reads service state")
            return
        if verbs & {"reboot", "poweroff", "halt", "kexec"}:
            findings.add(SYSTEM, f"{program} restarts or stops the machine", irreversible=True)
            return
    findings.add(PROCESS_CONTROL, f"{program} controls other processes or services")


def _mount_like(program, args, findings, context, depth, heredoc):
    if _targets(args) and not (program == "ip" and _targets(args)[1:2] in ([], ["show"], ["list"])):
        findings.add(SYSTEM, f"{program} changes the machine's configuration", irreversible=True)
    else:
        findings.add(READ, f"{program} reads the machine's configuration")


def _shell(program, args, findings, context, depth, heredoc):
    if "-c" in args or any(re.fullmatch(r"-[a-z]*c[a-z]*", arg) for arg in args):
        position = next(i for i, arg in enumerate(args) if arg == "-c" or re.fullmatch(r"-[a-z]*c[a-z]*", arg))
        if position + 1 < len(args):
            _assess_text(args[position + 1], findings, context, depth + 1)
            return
    if heredoc:
        _assess_text(heredoc, findings, context, depth + 1)
        return
    if not _targets(args):
        findings.blind(f"{program} runs commands read from its input")
        return
    findings.add(EXECUTE, f"{program} runs a script whose effects are not inspected")


def _interpreter(program, args, findings, context, depth, heredoc):
    code = ""
    for flag in ("-c", "-e", "--eval", "-p", "--print", "-E"):
        if flag in args and args.index(flag) + 1 < len(args):
            code = args[args.index(flag) + 1]
            break
    if program == "python3" and "-m" in args and not code:
        position = args.index("-m") + 1
        module = args[position] if position < len(args) else ""
        if module == "pip":
            _pip("pip", args[position + 1:], findings, context, depth, heredoc)
            return
        if module in ("http.server", "smtpd", "smtplib"):
            findings.add(NETWORK, f"python -m {module} serves or sends on the network")
            return
        findings.add(EXECUTE, f"python -m {module} runs project code")
        return
    if not code and heredoc and (not _targets(args) or _targets(args) == ["-"] or "-" in args):
        code = heredoc
    if not code:
        if not _targets(args) or "-" in args:
            findings.blind(f"{program} runs a program read from its input")
        else:
            findings.add(EXECUTE, f"{program} runs a script whose effects are not inspected")
        return
    findings.add(EXECUTE, f"{program} runs inline code")
    if _DELETE_CALLS.search(code):
        findings.add(DELETE, f"{program} inline code deletes files", irreversible=not context.reversible_deletes)
    if _NETWORK_CALLS.search(code):
        findings.add(NETWORK, f"{program} inline code reaches the network")
    if _PROCESS_CALLS.search(code):
        findings.blind(f"{program} inline code starts other commands")
    if _FILE_WRITE_CALLS.search(code):
        findings.add(WRITE, f"{program} inline code writes files")


_HANDLERS = {
    "mv": _mv, "cp": _cp, "find": _find, "xargs": _xargs, "parallel": _xargs, "sed": _sed, "gsed": _sed,
    "awk": _awk, "gawk": _awk, "mawk": _awk, "truncate": _truncate, "dd": _dd, "chmod": _chmod,
    "chown": _chmod, "chgrp": _chmod, "tar": _tar, "rsync": _rsync, "psql": _database, "mysql": _database,
    "sqlite3": _database, "duckdb": _database, "mongosh": _database, "mongo": _database,
    "redis-cli": _database, "docker": _docker, "podman": _docker, "kubectl": _kubectl,
    "npm": _package_manager, "pnpm": _package_manager, "yarn": _package_manager, "bun": _package_manager,
    "cargo": _package_manager, "gem": _package_manager, "go": _package_manager, "composer": _package_manager,
    "poetry": _package_manager, "pip": _pip, "pip3": _pip, "uv": _uv, "git": _git, "gh": _gh, "glab": _gh,
    "hub": _gh, "fly": _cloud, "flyctl": _cloud, "aws": _cloud, "gcloud": _cloud, "gsutil": _cloud,
    "az": _cloud, "terraform": _cloud, "pulumi": _cloud, "heroku": _cloud, "vercel": _cloud,
    "netlify": _cloud, "stripe": _cloud, "doctl": _cloud, "wrangler": _cloud, "supabase": _cloud,
    "railway": _cloud, "helm": _cloud, "ansible": _cloud, "ansible-playbook": _cloud,
    "curl": _http_client, "wget": _http_client, "http": _http_client, "https": _http_client,
    "xh": _http_client, "httpie": _http_client, "ssh": _ssh, "scp": _ssh, "sftp": _ssh,
    "mount": _mount_like, "ip": _mount_like, "ifconfig": _mount_like, "route": _mount_like,
}
