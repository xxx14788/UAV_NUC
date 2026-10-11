// t1_mtrace.c — T1 轻量 malloc 探针 v4（工程 v1.6 单元2 L2; heaptrack 停摆后自研案）
// v4: 弃 dlsym(ld.so 启动期段错误)改 __libc_* 直连; ≥T1_MTRACE_MIN(8192)B 分配记
//     backtrace(4 帧), free/realloc 配对查开放寻址表; 每 60s still-live 按(caller0,caller1)汇总。
#define _GNU_SOURCE
#include <execinfo.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <unistd.h>

extern void *__libc_malloc(size_t);
extern void __libc_free(void *);
extern void *__libc_calloc(size_t, size_t);
extern void *__libc_realloc(void *, size_t);
extern void *__libc_memalign(size_t, size_t);

#define MIN_DFL 8192
#define TBITS 19
#define TSZ (1u << TBITS)
#define TMASK (TSZ - 1)

static FILE *logf = NULL, *sumf = NULL;
static size_t min_sz = MIN_DFL;
static pthread_mutex_t mu = PTHREAD_MUTEX_INITIALIZER;
static int in_hook = 0;
static int ready = 0;

static struct { void *ptr; size_t sz; void *c0; void *c1; } tab[TSZ];

static double now_s(void) {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec + tv.tv_usec * 1e-6;
}
static void open_logs(void) {
    static int opening = 0;  // fopen 自身 malloc 重入守卫(v4 崩因: 无限递归爆栈)
    if (ready || opening) return;
    opening = 1;
    const char *o = getenv("T1_MTRACE_OUT"), *s = getenv("T1_MTRACE_SUM"), *m = getenv("T1_MTRACE_MIN");
    if (m) min_sz = (size_t)atol(m);
    if (o) { logf = fopen(o, "a"); if (logf) setvbuf(logf, NULL, _IONBF, 0); }
    if (s) { sumf = fopen(s, "a"); if (sumf) setvbuf(sumf, NULL, _IONBF, 0); }
    ready = 1;
}

static void tput(void *p, size_t sz, void *c0, void *c1) {
    unsigned i = ((unsigned)(uintptr_t)p >> 4) & TMASK;
    for (unsigned k = 0; k < 4096; k++) {
        unsigned j = (i + k) & TMASK;
        if (tab[j].ptr == NULL || tab[j].ptr == p) {
            tab[j].ptr = p; tab[j].sz = sz; tab[j].c0 = c0; tab[j].c1 = c1;
            return;
        }
    }
}
static int tdel(void *p, size_t *sz, void **c0) {
    unsigned i = ((unsigned)(uintptr_t)p >> 4) & TMASK;
    for (unsigned k = 0; k < 4096; k++) {
        unsigned j = (i + k) & TMASK;
        if (tab[j].ptr == p) {
            *sz = tab[j].sz; *c0 = tab[j].c0;
            tab[j].ptr = NULL;
            return 1;
        }
    }
    return 0;
}

static double last_sum = 0;
static void maybe_sum(void) {
    double t = now_s();
    if (t - last_sum < 60.0 || !sumf) return;
    last_sum = t;
    struct agg { void *c0, *c1; size_t bytes; size_t n; } aggs[512];
    int na = 0;
    pthread_mutex_lock(&mu);
    for (unsigned j = 0; j < TSZ; j++) {
        if (!tab[j].ptr) continue;
        int f = -1;
        for (int k = 0; k < na; k++)
            if (aggs[k].c0 == tab[j].c0 && aggs[k].c1 == tab[j].c1) { f = k; break; }
        if (f < 0 && na < 512) { f = na++; aggs[f].c0 = tab[j].c0; aggs[f].c1 = tab[j].c1; aggs[f].bytes = 0; aggs[f].n = 0; }
        if (f >= 0) { aggs[f].bytes += tab[j].sz; aggs[f].n++; }
    }
    pthread_mutex_unlock(&mu);
    fprintf(sumf, "SUM t=%.1f entries=%d\n", t, na);
    for (int k = 0; k < na; k++)
        fprintf(sumf, "LIVE c0=%p c1=%p bytes=%zu n=%zu\n", aggs[k].c0, aggs[k].c1, aggs[k].bytes, aggs[k].n);
}

// 记录段(调用方持锁)
static void log_alloc(void *r, size_t sz) {
    void *bt[5];
    int n = backtrace(bt, 5);
    tput(r, sz, n > 1 ? bt[1] : NULL, n > 2 ? bt[2] : NULL);
    if (logf) {
        fprintf(logf, "A %zu %p", sz, r);
        for (int i = 1; i < n; i++) fprintf(logf, " %p", bt[i]);
        fprintf(logf, "\n");
    }
}

void *malloc(size_t sz) {
    if (!ready) open_logs();
    void *r = __libc_malloc(sz);
    if (r && sz >= min_sz && !in_hook && logf) {
        in_hook = 1;
        pthread_mutex_lock(&mu);
        log_alloc(r, sz);
        pthread_mutex_unlock(&mu);
        in_hook = 0;
        maybe_sum();
    }
    return r;
}

void *calloc(size_t n, size_t sz) {
    if (!ready) open_logs();
    void *r = __libc_calloc(n, sz);
    size_t t = n * sz;
    if (r && t >= min_sz && !in_hook && logf) {
        in_hook = 1;
        pthread_mutex_lock(&mu);
        log_alloc(r, t);
        pthread_mutex_unlock(&mu);
        in_hook = 0;
        maybe_sum();
    }
    return r;
}

void *realloc(void *p, size_t sz) {
    if (!ready) open_logs();
    void *r = __libc_realloc(p, sz);
    if (!in_hook && (logf || sumf)) {
        in_hook = 1;
        size_t osz = 0;
        void *oc0 = NULL;
        pthread_mutex_lock(&mu);
        if (p && tdel(p, &osz, &oc0) && logf) fprintf(logf, "F %p %zu %p\n", p, osz, oc0);
        if (r && sz >= min_sz) log_alloc(r, sz);
        pthread_mutex_unlock(&mu);
        in_hook = 0;
        if (r && sz >= min_sz) maybe_sum();
    }
    return r;
}

void free(void *p) {
    if (!p) return;
    if (!ready) open_logs();
    if (!in_hook && (logf || sumf)) {
        in_hook = 1;
        size_t sz = 0;
        void *c0 = NULL;
        pthread_mutex_lock(&mu);
        if (tdel(p, &sz, &c0) && logf) fprintf(logf, "F %p %zu %p\n", p, sz, c0);
        pthread_mutex_unlock(&mu);
        in_hook = 0;
    }
    __libc_free(p);
}

int posix_memalign(void **memptr, size_t alignment, size_t size) {
    if (!ready) open_logs();
    if (alignment < sizeof(void *) || (alignment & (alignment - 1))) return 22;
    void *r = __libc_memalign(alignment, size);
    if (!r) return 12;
    *memptr = r;
    if (size >= min_sz && !in_hook && logf) {
        in_hook = 1;
        pthread_mutex_lock(&mu);
        log_alloc(r, size);
        pthread_mutex_unlock(&mu);
        in_hook = 0;
        maybe_sum();
    }
    return 0;
}

void *aligned_alloc(size_t alignment, size_t size) {
    if (!ready) open_logs();
    void *r = __libc_memalign(alignment, size);
    if (r && size >= min_sz && !in_hook && logf) {
        in_hook = 1;
        pthread_mutex_lock(&mu);
        log_alloc(r, size);
        pthread_mutex_unlock(&mu);
        in_hook = 0;
        maybe_sum();
    }
    return r;
}
