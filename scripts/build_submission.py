"""Build lab reports from the actual JSON/CSV evidence collected in this repo."""
import csv
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8-sig'))

def write(path, text):
    (ROOT / path).write_text(text.strip() + '\n', encoding='utf-8')

def main():
    image = read('evidence/part2/runtime.json')
    security = read('evidence/part4/runtime.json')
    shutdown = read('evidence/part5/health_shutdown.json')
    checklist = (ROOT / 'evidence/part6/readiness.txt').read_text(encoding='utf-8')
    checklist = checklist[checklist.index('  📋 Checklist Deliverable'):].strip()
    curl = (ROOT / 'evidence/part4/curl-http.txt').read_text(encoding='utf-8')
    p1 = read('evidence/part1/runtime.json')
    develop_answer = p1['runs'][0]['requests'][1]['body']['answer']
    burst_codes = [r['status'] for r in security['jwt']['burst']]
    public_path = ROOT / 'evidence/part6/public-api.json'
    public = read('evidence/part6/public-api.json') if public_path.exists() else None
    cloud_ok = bool(public and public['passed'])
    cloud_status = 'Hoàn tất Railway + Redis, public HTTP 200/200/401/200' if cloud_ok else 'Tạm bỏ theo yêu cầu người học; chưa có public URL'
    if cloud_ok:
        deploy_summary = (
            f"Đã deploy chính agent Part 6 lên Railway bằng tài khoản mới, kèm Redis trên mạng nội bộ.\n"
            f"Public URL: [{public['public_url']}]({public['public_url']}).\n"
            f"Bốn kiểm tra public thực tế: GET /health 200, GET /ready 200, POST /ask thiếu key 401, có key 200.\n"
            f"Xem [public-api.json](evidence/part6/public-api.json), [trạng thái Railway](evidence/part6/railway-deployment.json) "
            f"và [DEPLOYMENT.md](DEPLOYMENT.md). Ba ảnh deploy đã bổ sung; dashboard.png là bản xuất trạng thái Railway CLI."
        )
        public_summary = 'Ngoài PASS 12/12 local, URL Railway đã qua đủ bốn kiểm tra public; xem DEPLOYMENT.md và evidence/part6/public-api.json.'
        cloud_ai_log = '| Hoàn tất deploy Railway bằng tài khoản mới | AI tạo project/Redis/agent, đặt env, upload code và tạo public domain | Kiểm tra live HTTP 200/200/401/200, Redis nội bộ và hai service SUCCESS; lưu JSON và ảnh từ CLI/public API, không lưu secret vào Git |'
    else:
        deploy_summary = 'Cloud chưa hoàn tất; xem DEPLOYMENT.md. Các tài khoản thử ban đầu bị giới hạn trial/billing; chưa có URL public đã kiểm chứng.'
        public_summary = 'PASS 12/12 kiểm tra cấu hình public-ready; chưa tự chứng minh đã có URL cloud (theo DEPLOYMENT.md).'
        cloud_ai_log = '| Chọn Railway rồi chuyển Render | Chuẩn bị cấu hình deploy và thực hiện login CLI | Tài khoản ban đầu bị giới hạn trial/billing; trạng thái thật ghi trong DEPLOYMENT.md |'
    mission = f'''# Day 14 Lab — Mission Answers

Ngày thực hành: 25/11/2026 (GMT+7). Bài làm theo các điều chỉnh K5 trong README và CHECKPOINTS.
Các kết quả dưới đây do công cụ thực thi thu thập thật; không lấy số minh họa trong tài liệu làm kết quả.

| Checkpoint | Trạng thái |
|---|---|
| CP0 — Setup | Hoàn tất, repo public và Docker/Python Linux hoạt động |
| CP1 — Part 1 | Hoàn tất |
| CP2 — Docker | Hoàn tất |
| CP3 — Security | Hoàn tất |
| CP4 — Scaling/reliability | Hoàn tất |
| CP5 — Part 6 | PASS 12/12, 43/43 checks |
| CP6 — Cloud | {cloud_status} |
| CP7 — Benchmark local | Hoàn tất, eval cuối 23/23 |
| CP8 — Observability và hồ sơ local | Hoàn tất số đo/ảnh/báo cáo; chưa nộp link lên LMS |

## CP0 — Setup

- Repo làm việc: bản clone từ remote `worryveem/K5-L3A-DAY14-DoMinhHoang-2A202603554-Deployment-Benchmark-Observability`.
- Máy Windows có Docker Desktop dùng WSL2; chưa có distribution Ubuntu/Python trong WSL.
- Đã chạy Python Linux 3.11.18 trong container trên WSL2, `os.name = posix`.
- `docker run --rm hello-world`: xem [output](evidence/part0-docker-hello.txt).
- Không cần key LLM thật. Thông tin môi trường được ghi ở [evidence](evidence/docker-environment.json).

## Part 1 — Localhost vs Production (CP1)

### Exercise 1.1 — Anti-patterns trong develop/app.py

| Vị trí | Vấn đề | Hậu quả và cách xử lý |
|---|---|---|
| Dòng 17 | API key hardcode (key giả trong ví dụ) | Key thật sẽ nằm trong repo/lịch sử Git; lấy từ environment/secret store |
| Dòng 18 | URL DB chứa tài khoản/mật khẩu và localhost | Lộ credential, phụ thuộc máy chạy; đưa connection string ra env |
| Dòng 21–22 | DEBUG/MAX_TOKENS cố định | Không đổi cấu hình theo môi trường bằng cùng artifact được |
| Dòng 33–38 | Dùng print; dòng 34 in cả key | Khó lọc log, phát tán secret; log có cấu trúc và loại bỏ credential |
| Các route dòng 25–39 | Thiếu /health và /ready | Hệ thống vận hành thiếu endpoint để kiểm tra sống/sẵn sàng |
| Dòng 51 | Bind localhost | Không nhận kết nối tới địa chỉ mạng container từ bên ngoài |
| Dòng 52 | Port luôn là 8000 | Không sử dụng PORT do cloud inject |
| Dòng 53 | reload=True cố định | Chạy reloader không cần thiết trong production |
| Toàn file | Không có lifespan cleanup của app | Chưa có chỗ đóng connection/flush tài nguyên khi tắt |

Không kết luận mọi lần tắt develop đều đột ngột: Uvicorn vẫn có shutdown mặc định.
Thiếu ở bản develop là lifecycle/cleanup riêng của ứng dụng.

### Exercise 1.2 — Chạy basic version

Đã cài dependencies và chạy nguyên `python app.py` trong container Linux, rồi gọi HTTP thật bên trong container
(cần gọi nội bộ vì ví dụ bind localhost). Không chỉnh code mẫu Part 1.

```bash
cd 01-localhost-vs-production/develop
pip install -r requirements.txt
python app.py
# Terminal khác, cùng môi trường mạng:
curl -i -X POST 'http://localhost:8000/ask?question=Hello'
```

Kết quả thực tế: HTTP 200, `answer`: {develop_answer}

| Request develop | HTTP |
|---|---:|
| GET / | 200 |
| POST /ask?question=Hello | 200 |
| POST /ask?question=What%20is%20Docker%3F | 200 |
| POST /ask với JSON question, không có query | 422 |
| GET /health | 404 |
| GET /ready | 404 |

Develop nhận `question` qua query; JSON-only bị 422 vì FastAPI báo thiếu query parameter.
Log có dòng `Using key`, đã che giá trị cả khi chỉ là key giả. Toàn bộ request/response và log:
[evidence/part1/runtime.json](evidence/part1/runtime.json).

### Exercise 1.3 — Bảng so sánh

| Feature | Develop | Production mẫu | Tại sao quan trọng? |
|---|---|---|---|
| Config | Hằng số trong app.py | Settings đọc os.getenv trong config.py | Một artifact dùng được qua dev/staging/production |
| Secrets | Key/DB credential hardcode và key bị in log | Lấy key từ env, log chỉ độ dài câu hỏi | Tránh đưa credential vào source và log |
| Network/port | localhost:8000 | HOST mặc định 0.0.0.0, PORT từ env | Nhận traffic ngoài container và theo port cloud |
| Reload | Luôn bật | Theo DEBUG, mặc định false | Production không chạy file watcher |
| Liveness | Không có /health | /health có uptime, version, environment | Cho nền tảng kiểm tra process |
| Readiness | Không có /ready | Cờ is_ready trong lifespan | Chỉ route traffic khi instance sẵn sàng |
| Logging | print, có key | Có ý định log JSON, không log key | Thuận tiện truy vấn log; xem hạn chế thực tế bên dưới |
| Shutdown | Không có cleanup riêng | lifespan startup/shutdown | Quản lý vòng đời và dọn tài nguyên |
| Input | Query question | JSON question; rỗng trả 422 | Hợp đồng request rõ hơn |
| CORS | Không cấu hình | Danh sách origin từ env | Giới hạn truy cập từ JavaScript trên trình duyệt |

Đã chạy bản production với PORT=8001, ENVIRONMENT=production, DEBUG=false và key tạm qua env.
GET /, /health, /ready và POST /ask hợp lệ đều 200; JSON thiếu question trả 422.
SIGTERM sau các request làm process thoát mã 0. Đây chưa phải thí nghiệm in-flight (thí nghiệm đó ở Part 5/6).

Những giới hạn quan sát được của bản mẫu: warning trong config.py được ghi trước basicConfig nên root logger
đã có handler; lần chạy này chưa xuất hiện log JSON của app. /ready chỉ kiểm cờ, chưa ping dependency.
AGENT_API_KEY được validate trong config nhưng chưa gắn auth vào /ask (gọi không header vẫn 200).
File .env không tự được nạp chỉ vì có python-dotenv trong requirements; dùng env thực hoặc loader rõ ràng.
/metrics ở Part 1 trả JSON đơn giản, chưa phải exposition format Prometheus như Part 7.

Thảo luận: public key thật có thể bị quét và lạm dụng, cần revoke/rotate chứ xóa file chưa đủ.
Stateless quan trọng vì mỗi instance có RAM riêng; state chung phải ở Redis/DB.
Dev/prod parity nghĩa là giữ runtime, dependency và backing service gần nhau, với cấu hình khác qua env.

## Part 2 — Docker (CP2)

### Exercise 2.1

1. Base image: `python:3.11`; đây là Python runtime và các thư viện hệ điều hành làm nền image.
2. Working directory: `/app`; các lệnh COPY/RUN/CMD với đường dẫn tương đối dựa vào đây.
3. COPY requirements trước source để Docker tái sử dụng layer cài dependency khi chỉ code thay đổi.
4. CMD đặt lệnh/đối số mặc định, dễ bị thay bởi đối số docker run. ENTRYPOINT đặt executable chính;
   với exec form, đối số docker run thường thay CMD và được nối vào ENTRYPOINT. Dùng exec form để chuyển signal đúng.

### Exercise 2.2–2.3 — Build và đo image

```bash
# Từ gốc repo:
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
docker build -f 02-docker/production/Dockerfile -t my-agent:advanced .
docker image inspect my-agent:develop my-agent:advanced --format '{{{{.RepoTags}}}} {{{{.Size}}}}'
```

| Image | Bytes thực đo | MiB (bytes / 1024²) |
|---|---:|---:|
| Develop | {image['image_sizes']['my-agent:develop']['bytes']} | {image['image_sizes']['my-agent:develop']['MiB']} |
| Production | {image['image_sizes']['my-agent:advanced']['bytes']} | {image['image_sizes']['my-agent:advanced']['MiB']} |

Giảm **{image['size_reduction_percent']}%**, tính `(develop - production) / develop × 100`.
Stage builder cài compiler/dependencies; runtime chỉ lấy packages đã cài và source cần chạy.
Không mang gcc, header và layer build sang image cuối; base slim cũng nhỏ hơn bản Python đầy đủ.
Hai container riêng đã trả 200 khi gọi agent; [kết quả](evidence/part2/runtime.json).

### Exercise 2.4 — Stack và giao tiếp

```mermaid
flowchart LR
  Client -->|HTTP :80| Nginx
  Nginx -->|agent:8000| Agent
  Agent -. REDIS_URL .-> Redis
  Agent -. QDRANT_URL .-> Qdrant
```

Đã chạy `docker compose -p k5-day14-docker up -d` tại thư mục production, có `.env.local` trống được ignore.
Stack gồm agent, Redis, Qdrant, Nginx trên mạng internal; DNS service name dùng cho giao tiếp nội bộ.
Các biến REDIS_URL/QDRANT_URL chuẩn bị đường kết nối; app mẫu chưa thực hiện retrieval/session qua chúng.
GET /health và POST /ask qua Nginx cổng 80 đều 200, xem file runtime ở trên. Redis/Qdrant có named volume.
Healthcheck đánh dấu container unhealthy; Docker restart policy không tự restart chỉ vì unhealthy.

## Part 3 — Cloud Deployment (CP6)

{deploy_summary}

| Railway TOML | Render YAML |
|---|---|
| builder=DOCKERFILE, dùng context Part 6 | web runtime=docker, rootDir=06-lab-complete |
| healthcheckPath=/health | healthCheckPath=/health |
| Tạo Redis service và REDIS_URL qua platform | Blueprint mô tả keyvalue và fromService connectionString |
| Secret đặt ngoài TOML | AGENT_API_KEY dùng generateValue, không ghi giá trị |

Exercise 3.3 — Cloud Run CI/CD (đọc cấu hình, không deploy GCP):

1. Cloud Build cài dependency và chạy pytest trước bước build.
2. Docker build image gắn COMMIT_SHA/latest, tận dụng layer cache.
3. Push image lên registry để môi trường chạy tải được đúng artifact.
4. gcloud run deploy dùng image COMMIT_SHA, region asia-southeast1, env và Secret Manager.
5. service.yaml mô tả concurrency 80, min/max instance 1/10, resource limit và probe /health, /ready.

Lưu ý thực tế: step shell test trong mẫu nên có `set -e` để lệnh echo cuối không che exit code pytest thất bại.

## Part 4 — API Security (CP3)

### Exercise 4.1–4.3

Đã chạy API-key sample và JWT sample riêng trên cổng 8014 để tránh xung đột.
API key tạm được truyền bằng env; JWT lấy ở POST /auth/token bằng user mẫu student/demo123, không lưu token.
Kết quả: API key thiếu → 401, đúng → 200; JWT thiếu → 401; burst 12 request có
**{burst_codes.count(200)} lần 200 và {burst_codes.count(429)} lần 429**. Header Retry-After có trong response 429.

Output thật từ curl -i (không có credential trong request được lưu):

```http
{curl.strip()}
```

Rate limiter mẫu dùng sliding-window log: deque timestamp, loại các request quá 60 giây rồi đếm phần còn lại.
Student 10 request/phút; admin 100 request/phút. Admin có hạn mức cao hơn, **không được bypass hoàn toàn**.
State in-memory trong ví dụ chỉ phù hợp demo; Part 6 chuyển sang Redis để nhiều worker chia sẻ và chống reset khi restart.
API-key sample trả 403 khi key sai, khác yêu cầu Part 6 là thiếu/sai đều 401.

### Exercise 4.4 — Cost guard

Rate limit hạn chế tốc độ gọi, không biết mỗi request dùng bao nhiêu token. Cost guard cộng chi phí token input/output
và chặn khi hết ngân sách, nên cần cả hai. Với ngân sách $10/tháng cho mỗi user, dùng Redis key chứa user + tháng UTC,
kiểm `current + estimated_cost <= 10` và ghi nhận reservation nguyên tử bằng Lua; đặt TTL đủ dài qua kỳ quyết toán.
Kỳ mới dùng key mới; sau khi gọi model cần reconcile reservation với usage thật.

Theo K5, Part 4 chạy và giải thích code mẫu: mẫu dùng budget ngày trong RAM, user vượt trả 402, global vượt trả 503.
Phần triển khai nộp Part 6 dùng Redis với budget ngày/tháng toàn service, vượt trả 402, chi phí mock ước lượng theo ký tự.
Giới hạn còn lại: check trước và record sau chưa reserve ngân sách cho request đồng thời; chi phí có thể vượt thêm bởi
các request đã được chấp nhận. Production thật cần reservation nguyên tử như mô tả trên.

## Part 5 — Scaling & Reliability (CP4)

Exercise 5.1: /health là liveness, không phụ thuộc Redis. /ready là readiness và phải 503 khi dependency chưa sẵn sàng.
Ví dụ develop dùng cờ; agent Part 6 ping Redis với timeout. Khi Redis chết, restart mọi agent không sửa được Redis,
nên /health vẫn 200 để tránh restart loop, trong khi /ready ngăn route request vào instance không sẵn sàng.

Exercise 5.2: đã gửi request rồi SIGTERM trong khi request còn xử lý. Request trả **{shutdown['in_flight']['status']}**;
process kết thúc, return code thực tế của Uvicorn CLI ví dụ là **{shutdown['sigterm_exit_code']}** trên Linux.
Đã sửa handler logging-only trong mẫu vì nó thay handler Uvicorn khi import qua CLI và làm process không thoát.
Cleanup nằm trong lifespan; không dùng SIGKILL cho đường tắt bình thường.
Part 6 có kiểm tra mạnh hơn: in-flight 200, exit 0, Docker stop 1 giây; xem checklist bên dưới.

Exercise 5.3: state trong RAM làm các instance thấy các history khác nhau. Redis là backing service chung nên
instance nhận request tiếp theo vẫn đọc được session. Scale agent không đòi sticky session để giữ history.

Exercise 5.4–5.5: đã chạy 3 instance với project k5-day14-scaling, Nginx cổng 8080, POST /chat;
script gốc gửi 5 request cùng session qua **3 instance** và đọc đủ **10 message** (5 user + 5 assistant).
Script không tự kill instance, vì vậy không dùng kết quả này để khẳng định đã kiểm thử failover.
[Output nguyên bản](evidence/part5/stateless.txt), [health/shutdown](evidence/part5/health_shutdown.json).

## Part 6 — Final Project (CP5)

Làm trực tiếp trong 06-lab-complete/app. Auth so sánh key constant-time; rate limit sliding window dùng Redis TIME,
sorted set và Lua nguyên tử; key được hash trước khi làm Redis key. Cost ngày/tháng lưu Redis có TTL.
Đã hoàn thiện Dockerfile multi-stage, non-root, HEALTHCHECK, PORT, Compose Redis và hai cấu hình cloud.
Redis không cần hoạt động lúc import/startup; lỗi khi xử lý state trả 503 không lộ connection string/stack trace.

Lệnh chấm đầy đủ chạy bằng Python Linux với Docker daemon thực, script chấm không sửa:

```bash
cd 06-lab-complete
python check_production_ready.py
```

```text
{checklist}
```

Log đầy đủ: [readiness.txt](evidence/part6/readiness.txt). Image 238 MiB theo script chấm.
Kiểm tra bổ sung Compose: input rỗng, toàn khoảng trắng, sai kiểu đều 422; health/ready 200, thiếu key 401.
20 request đồng thời qua 2 worker cho đúng 10 lần 200 và 10 lần 429:
[api-validation.json](evidence/part6/api-validation.json).
{public_summary}

## Part 7 — Benchmark & Observability (CP7–CP8)

Xem [BENCHMARK_REPORT.md](BENCHMARK_REPORT.md), các JSON trong reports, CSV trong benchmark-results và ảnh screenshots.
Đã bổ sung Histogram agent_question_length_chars, không dùng độ dài câu hỏi làm label.
Không sửa golden_dataset.jsonl hoặc check_production_ready.py.

## AI log

| Yêu cầu gửi AI | Kết quả AI cung cấp | Sửa và kiểm tra thực tế |
|---|---|---|
| Đọc lab, giải thích các bước | Đối chiếu tài liệu K5 và lập thứ tự checkpoint | Đọc README/RULES/CHECKPOINTS/SUBMISSION/RUBRIC và code mẫu |
| Làm Part 1, sau đó toàn bộ checkpoint/part | AI viết code Part 6, metric/KB/CI, sửa 2 lỗi mẫu, thu thập và tổng hợp báo cáo | AI trực tiếp chạy HTTP, Docker build/Compose, script chấm gốc, eval/load/Locust, promtool và browser screenshot; đường dẫn bằng chứng đi kèm từng phần |
| Chọn Railway rồi chuyển Render | Chuẩn bị cấu hình deploy và thực hiện login CLI | Railway bị chặn bởi trial hết hạn; trạng thái thật của cloud ghi trong DEPLOYMENT.md |
{cloud_ai_log}

Các thao tác tự động trên do AI thực hiện trong workspace. Chưa có xác nhận người học đã tự đọc hiểu từng đoạn code;
người học cần đối chiếu code và bằng chứng trước khi nộp/giải thích với Lab Coach. Không khai các thao tác AI là tự làm tay.
'''
    write('MISSION_ANSWERS.md', mission)

    # All numerical tables are rendered directly from source evidence.
    rows = []
    for c in [1, 10, 50, 100]:
        r = read(f'reports/load_v2_c{c}.json')
        l = r['latency_ms']
        rows.append(f"| {c} | {r['rps']} | {l['p50']} | {l['p95']} | {l['p99']} | {r['error_rate']:.2%} | {'PASS' if r['slo']['passed'] else 'FAIL'} |")
    slow_rows = []
    for value in ['0', '0.03', '0.1']:
        r = read(f'reports/load_v2_slow_{value}.json')
        l = r['latency_ms']
        slow_rows.append(f"| {value} | {l['avg']} | {l['p95']} | {l['p99']} |")
    evals = [read(f'reports/eval_{name}.json') for name in ['v1', 'v2', 'v2_fixed']]
    eval_rows = []
    fields = [('Accuracy', lambda e: f"{e['passed']}/{e['total']} ({e['accuracy']:.2%})"),
              ('Avg tokens / câu', lambda e: str(e['avg_tokens'])),
              ('Tổng cost USD', lambda e: str(e['total_cost_usd'])),
              ('Cost / câu đúng USD', lambda e: str(e['cost_per_correct_usd'])),
              ('Quality gate', lambda e: 'PASS' if e['quality_gate']['passed'] else 'FAIL')]
    for label, render in fields:
        eval_rows.append('| ' + label + ' | ' + ' | '.join(render(e) for e in evals) + ' |')
    traces = read('evidence/part7/selected-traces.json')
    slow = traces['slow']
    total_us = max(s['startTime'] + s['duration'] for s in slow['spans']) - min(s['startTime'] for s in slow['spans'])
    # Ignore enclosing spans when identifying the slowest actual operation.
    operation = max((s for s in slow['spans'] if s['operationName'].startswith(('chat ', 'agent.retrieve_context'))), key=lambda s: s['duration'])
    logs = read('evidence/part7/trace-logs.json')
    alerts = read('evidence/part7/alert-experiments.json')
    prometheus = read('evidence/part7/prometheus-baseline.json')
    def prom_number(name):
        return float(prometheus[name]['response']['data']['result'][0]['value'][1])
    scale_rows = []
    scale_stats = []
    for count in [1, 3]:
        with (ROOT / f'benchmark-results/scale_{count}_stats.csv').open(encoding='utf-8-sig') as stream:
            row = next(r for r in csv.DictReader(stream) if r['Name'] == 'Aggregated')
        scale_stats.append(row)
        scale_rows.append(f"| {count} | {float(row['Requests/s']):.2f} | {row['50%']} | {row['95%']} | {row['99%']} | {row['Failure Count']}/{row['Request Count']} |")
    report = f'''# Benchmark & Observability Report — Day 14

**Họ tên:** Đỗ Minh Hoàng — 2A202603554

**Ngày chạy:** 25/11/2026 (GMT+7)
**Môi trường:** Windows, Docker Desktop 29.8.0/WSL2, Linux x86_64; Docker thấy 16 CPU, 8.17 GB RAM;
Python 3.11.18. Local benchmark chạy trong container Linux network=host.
Máy đồng thời có hoạt động build/test trong quá trình lab; đây là số đo trên máy thực hành, chưa phải benchmark môi trường cô lập.

## 1. SLO của agent

| SLI | SLO | Lý do |
|---|---|---|
| p95 /ask | ≤ 500 ms | Kiểm tra phần lớn người dùng nhận phản hồi nhanh |
| Error rate /ask | ≤ 2% | Có mock lỗi upstream mặc định 1%, vẫn cần giới hạn lỗi |
| Accuracy | CI ≥ 85%, nghiệm thu bản sửa 100% và không regression | Ngăn chất lượng giảm; bộ nghiệm thu cố định 23 câu |

Ngưỡng load test là ngưỡng mặc định thực tế của script (≤), không thay đổi để biến FAIL thành PASS.
Alert dùng ngưỡng riêng với thời gian for, không đồng nhất ngưỡng SLO của benchmark.

## 2. Benchmark hiệu năng

### 2.1 Concurrency vs latency — v2

Mỗi lần 300 request, MOCK_ERROR_RATE=0.01, MOCK_SLOW_RATE=0.03.

| Concurrency | RPS | p50 ms | p95 ms | p99 ms | Error rate | SLO |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

RPS không tăng tuyến tính: 1→50 tăng nhờ chồng thời gian chờ I/O, nhưng 100 giảm và tail latency tăng mạnh.
Quan sát này phù hợp với giới hạn tài nguyên/lập lịch và overhead phía client/server trên máy dùng chung;
chưa có profiler nên không kết luận duy nhất CPU hay event loop là nguyên nhân.
Kết quả FAIL ở concurrency 100 được giữ nguyên. Cần giảm concurrency hoặc tăng capacity và đo lại trước khi nhận tải đó.

### 2.2 Tail latency

Cùng 300 request, concurrency=20, MOCK_ERROR_RATE=0.01; restart v2 khi đổi MOCK_SLOW_RATE.

| MOCK_SLOW_RATE | avg ms | p95 ms | p99 ms |
|---|---|---|---|
{chr(10).join(slow_rows)}

Average pha loãng số request rất chậm; percentile cao phơi bày nhóm người dùng chờ lâu.
Khi tỉ lệ chậm vượt khoảng 5%, p95 cũng bị đẩy vào nhóm request chậm; p99 nhạy với đuôi phân bố từ tỉ lệ thấp hơn.
Mỗi lần chỉ 300 mẫu và có ngẫu nhiên, nên không dùng một lần chạy để chứng minh phân bố ổn định.

## 3. Benchmark chất lượng

Eval tắt lỗi ngẫu nhiên và tail injection (MOCK_ERROR_RATE=0, MOCK_SLOW_RATE=0) để so sánh kiến thức.
Không dùng 23 mẫu eval để kết luận hiệu năng. Load test ở mục 2 vẫn giữ fault mặc định.

| Chỉ số | v1 | v2 ban đầu | v2 sửa KB |
|---|---|---|---|
{chr(10).join(eval_rows)}

| ID sai ban đầu | Keyword thiếu | Sửa |
|---|---|---|
| security-02 | token, hết hạn, chữ ký | Thêm tài liệu phân biệt API key với JWT, chữ ký và expiry |
| scaling-03 | cpu, memory, custom metrics | Thêm tài liệu HPA/autoscaling theo resource và custom metrics |

Sửa KNOWLEDGE_BASE ở develop và đồng bộ production; không sửa golden dataset.
Kết quả cuối: {evals[2]['passed']}/23, regression={evals[2]['quality_gate']['regressions']}.
V2 tốn nhiều token/câu hơn vì thêm context nhưng cost/câu đúng thấp hơn v1 trong bộ đánh giá này.
Chi phí là mô phỏng theo bảng giá trong mock, không phải hóa đơn nhà cung cấp.

Job [.github/workflows/eval.yml](.github/workflows/eval.yml) khởi động v2, đợi /health, chạy eval với
--min-accuracy 0.85 và baseline đã sửa. Exit code 1 làm CI job fail nếu thiếu accuracy hoặc có regression.
Để chặn merge, GitHub branch protection phải yêu cầu job này; chưa đổi branch protection trong tài khoản.
Bước shell thực tế của workflow cũng đã được chạy trong môi trường Linux local và exit 0:
[ci-local.txt](evidence/part7/ci-local.txt), [ci_eval.json](reports/ci_eval.json).

### 3.1 Exercise 7.1 — Metrics

- Counter: http_requests_total, chỉ tăng; dùng rate để tính request/giây.
- Gauge: agent_in_flight_requests, tăng/giảm theo số request đang xử lý.
- Histogram: http_request_duration_seconds và metric mới agent_question_length_chars.
- Thêm QUESTION_LENGTH.observe(len(body.question)); độ dài được bucket hóa, không làm label.
- route.path gom series theo template; URL không khớp gán unmatched. Dùng URL thật khiến bot quét URL lạ
  tạo hàng nghìn series, tăng cardinality và RAM Prometheus.

## 4. Observability stack

### 4.1 Bằng chứng và câu trả lời Exercise 7.4

- [Grafana có tải](screenshots/grafana-dashboard.png)
- [Jaeger trace chậm](screenshots/jaeger-slow-trace.png)
- [Jaeger trace lỗi có exception](screenshots/jaeger-error-trace.png)
- [Prometheus ít nhất 2 alert cùng firing](screenshots/prometheus-alert-firing.png)

Tại snapshot query ở [prometheus-baseline.json](evidence/part7/prometheus-baseline.json),
p95={prom_number('p95_seconds')*1000:.2f} ms và avg={prom_number('avg_seconds')*1000:.2f} ms.
Histogram percentile là nội suy theo bucket và khác latency percentile tính từ từng request trong load_test.py.
Screenshot chụp ở thời điểm khác nên các giá trị động không nhất thiết bằng snapshot query.
Request/s hai instance gần nhau; số cụ thể nằm trong query requests_per_instance, phù hợp Nginx phân phối đều.
Input token/s lớn hơn output vì prompt có system prompt + câu hỏi + retrieval context, trong khi câu trả lời ngắn.
GET /metrics qua Nginx trả 404 theo rule bảo vệ; Prometheus scrape trực tiếp agent trong mạng Docker.

### 4.2 Thí nghiệm gây sự cố

Giữ tải Locust 30 user, ramp-up 5. Áp dụng A và D trong cùng một đợt để thu ảnh hai alert đồng thời;
đây không phải thiết kế cô lập nguyên nhân từng biến. Mốc bắt đầu trước khi recreate service, bao gồm startup/ramp-up;
poll API mỗi 5 giây nên thời gian phát hiện có sai số khoảng một chu kỳ poll.

| Thí nghiệm | Alert | Lần đầu quan sát firing từ mốc bắt đầu |
|---|---|---:|
| A: MOCK_ERROR_RATE=0.2 | AgentHighErrorRate | {alerts['first_firing_s']['AgentHighErrorRate']} s |
| D: docker pause một trong hai instance | AgentInstanceDown | {alerts['first_firing_s']['AgentInstanceDown']} s |

Unit test rule bằng promtool: SUCCESS, [output](evidence/part7/alert-rule-tests.txt).
[Lịch sử API alert và timestamp](evidence/part7/alert-experiments.json) chứng minh cùng thời điểm hai alert firing.
B/C không thực hiện như các thí nghiệm độc lập; không ghi số giả cho các hàng này.
Trong đợt quan sát còn có LLMCostBurnRateHigh firing tạm thời, nhưng không dùng để thay thế hai thí nghiệm A/D.

Pause giữ container trong Docker DNS nên Prometheus còn target và thấy up=0; stop có thể làm target biến mất.
Các lỗi 504 ở Nginx chưa được agent xử lý xong nên metric riêng của agent không đếm hết lỗi người dùng thấy.
Sau thí nghiệm đã unpause và khôi phục MOCK_ERROR_RATE=0.01/MOCK_SLOW_RATE=0.03 trước benchmark scaling.
Đổi sang v1 có thể làm quality giảm mà metrics hạ tầng vẫn xanh: cần eval định kỳ, quality gate và giám sát chất lượng câu trả lời.

### 4.3 Debug bằng trace

- Trace chậm: `{slow['traceID']}`.
- Tổng thời gian: {total_us/1000:.3f} ms.
- Bước xử lý chậm nhất: `{operation['operationName']}`, {operation['duration']/1000:.3f} ms,
  chiếm {operation['duration']/total_us:.2%} tổng trace. Đây là span thao tác; POST /ask và agent.run là span bao ngoài.
- Trace lỗi: `{traces['error']['traceID']}`, span chat có event exception LLMError/upstream 503.
- JSON log thật cùng trace_id, lấy trước khi recreate container:

```json
{json.dumps(logs['slow'][0], ensure_ascii=False)}
```

```json
{json.dumps(logs['error'][0], ensure_ascii=False)}
```

[Trace export](evidence/part7/selected-traces.json), [log liên kết](evidence/part7/trace-logs.json).
Script thu trace dùng API v3 của Jaeger 2.23 theo [API chính thức](https://www.jaegertracing.io/docs/2.23/architecture/apis/).

## 5. Benchmark scaling — Locust headless

100 user, ramp-up 10 user/s, 2 phút mỗi lượt; cùng fault mặc định và cùng model/version.
Chờ Docker DNS cập nhật 15 giây sau khi scale. Bảng dưới dùng dòng Aggregated gồm /ask và /health.
Muốn phân tích riêng nghiệp vụ cần đối chiếu dòng /ask trong CSV.

| Instance | RPS | p50 ms | p95 ms | p99 ms | Failures / Requests |
|---|---|---|---|---|---|
{chr(10).join(scale_rows)}

RPS ratio 3/1 = {float(scale_stats[1]['Requests/s'])/float(scale_stats[0]['Requests/s']):.3f}.
Trong lần đo này, p95 giảm từ {scale_stats[0]['95%']} ms xuống {scale_stats[1]['95%']} ms,
tương đương {1-float(scale_stats[1]['95%'])/float(scale_stats[0]['95%']):.2%}; p99 vẫn là
{scale_stats[1]['99%']} ms nên tail latency của mock LLM vẫn còn.
Tăng instance không mặc nhiên tăng throughput 3 lần: Locust giữ cùng 100 user và có wait_time 0.5–2 giây;
mock LLM vẫn có latency nền/tail. Đánh giá cải thiện p95 theo số đo thực tế, không chỉ nhìn replica count.
Thí nghiệm này không tìm maximum throughput vì tải có thời gian nghỉ và user cố định.
Locust trả exit code 1 khi có request lỗi do mock; CSV vẫn được ghi và các lỗi vẫn được giữ trong bảng.

## 6. Kết luận

1. Percentile giúp nhìn thấy nhóm request chậm mà average che giấu; tải quá cao có thể làm SLO fail.
2. Eval phát hiện sai kiến thức dù hệ thống còn khỏe; cost/câu đúng giúp so phiên bản công bằng hơn.
3. Metrics phát hiện vấn đề tổng thể, trace xác định bước chậm và trace_id nối về log chi tiết.

Production thật cần thêm metric ở ingress để bắt 504, queue depth, usage thật từ provider, reservation budget nguyên tử,
sampling trace theo tải và eval đại diện hơn 23 câu. Không suy rộng kết quả mock thành năng lực mô hình thật.
'''
    write('BENCHMARK_REPORT.md', report)
    print('Built MISSION_ANSWERS.md and BENCHMARK_REPORT.md from evidence.')

if __name__ == '__main__':
    main()
