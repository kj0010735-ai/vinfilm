// VINFILM 리모트.app의 실행 파일 — build_app.sh가 cc로 컴파일해 Contents/MacOS/launcher로 넣는다.
// 파이썬 서버를 exec로 바꿔치기하지 않고 '자식 프로세스'로 띄우는 게 핵심이다:
// macOS는 손쉬운 사용 권한을 "책임 프로세스"(이 앱) 기준으로 확인하는데, exec하면 프로세스가 python으로 바뀌어
// 이 앱에 준 권한이 안 먹고 python 권한을 따로 요구한다. 자식으로 띄우면 이 앱의 권한을 그대로 물려받는다.
#include <limits.h>
#include <signal.h>
#include <spawn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
#ifdef __APPLE__
#include <mach-o/dyld.h>
#endif

extern char **environ;
static pid_t child = 0;

static void forward(int sig) {
    if (child > 0) kill(child, sig);
}

static int self_path(char *out, size_t n) {
#ifdef __APPLE__
    char raw[PATH_MAX];
    uint32_t size = sizeof raw;
    if (_NSGetExecutablePath(raw, &size) != 0) return -1;
    return realpath(raw, out) ? 0 : -1;
#else
    ssize_t len = readlink("/proc/self/exe", out, n - 1);
    if (len < 0) return -1;
    out[len] = 0;
    return 0;
#endif
}

int main(void) {
    char exe[PATH_MAX], script[PATH_MAX];
    if (self_path(exe, sizeof exe) != 0) return 1;
    // …/Contents/MacOS/launcher → …/Contents/Resources/remote_server.py
    for (int i = 0; i < 2; i++) {
        char *slash = strrchr(exe, '/');
        if (!slash) return 1;
        *slash = 0;
    }
    snprintf(script, sizeof script, "%s/Resources/remote_server.py", exe);

    const char *pythons[] = {"/usr/bin/python3", "/opt/homebrew/bin/python3", "/usr/local/bin/python3"};
    for (size_t i = 0; i < sizeof pythons / sizeof *pythons; i++) {
        if (access(pythons[i], X_OK) != 0) continue;
        char *argv[] = {(char *)pythons[i], script, NULL};
        if (posix_spawn(&child, pythons[i], NULL, NULL, argv, environ) != 0) continue;
        signal(SIGTERM, forward);
        signal(SIGINT, forward);
        signal(SIGHUP, forward);
        int status = 0;
        while (waitpid(child, &status, 0) < 0) {}
        return WIFEXITED(status) ? WEXITSTATUS(status) : 1;
    }
    char *msg[] = {"/usr/bin/osascript", "-e",
                   "display dialog \"python3를 찾을 수 없어요. 터미널에서 xcode-select --install 을 실행해 설치해 주세요.\" buttons {\"확인\"}",
                   NULL};
    posix_spawn(&child, msg[0], NULL, NULL, msg, environ);
    return 1;
}
