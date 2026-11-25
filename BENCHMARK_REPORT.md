# Benchmark & Observability Report — Day 14

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
| 1 | 4.05 | 193.6 | 224.3 | 1709.7 | 1.33% | PASS |
| 10 | 35.56 | 194.0 | 234.5 | 1701.7 | 0.67% | PASS |
| 50 | 97.15 | 225.1 | 387.3 | 1729.3 | 0.67% | PASS |
| 100 | 40.55 | 1163.9 | 5202.6 | 5600.9 | 1.33% | FAIL |

RPS không tăng tuyến tính: 1→50 tăng nhờ chồng thời gian chờ I/O, nhưng 100 giảm và tail latency tăng mạnh.
Quan sát này phù hợp với giới hạn tài nguyên/lập lịch và overhead phía client/server trên máy dùng chung;
chưa có profiler nên không kết luận duy nhất CPU hay event loop là nguyên nhân.
Kết quả FAIL ở concurrency 100 được giữ nguyên. Cần giảm concurrency hoặc tăng capacity và đo lại trước khi nhận tải đó.

### 2.2 Tail latency

Cùng 300 request, concurrency=20, MOCK_ERROR_RATE=0.01; restart v2 khi đổi MOCK_SLOW_RATE.

| MOCK_SLOW_RATE | avg ms | p95 ms | p99 ms |
|---|---|---|---|
| 0 | 209.5 | 260.6 | 276.9 |
| 0.03 | 263.5 | 261.0 | 1717.4 |
| 0.1 | 335.4 | 1691.3 | 1725.3 |

Average pha loãng số request rất chậm; percentile cao phơi bày nhóm người dùng chờ lâu.
Khi tỉ lệ chậm vượt khoảng 5%, p95 cũng bị đẩy vào nhóm request chậm; p99 nhạy với đuôi phân bố từ tỉ lệ thấp hơn.
Mỗi lần chỉ 300 mẫu và có ngẫu nhiên, nên không dùng một lần chạy để chứng minh phân bố ổn định.

## 3. Benchmark chất lượng

Eval tắt lỗi ngẫu nhiên và tail injection (MOCK_ERROR_RATE=0, MOCK_SLOW_RATE=0) để so sánh kiến thức.
Không dùng 23 mẫu eval để kết luận hiệu năng. Load test ở mục 2 vẫn giữ fault mặc định.

| Chỉ số | v1 | v2 ban đầu | v2 sửa KB |
|---|---|---|---|
| Accuracy | 1/23 (4.35%) | 21/23 (91.30%) | 23/23 (100.00%) |
| Avg tokens / câu | 57.3 | 109.3 | 113.7 |
| Tổng cost USD | 0.000406 | 0.000764 | 0.00079 |
| Cost / câu đúng USD | 0.00040635 | 3.639e-05 | 3.436e-05 |
| Quality gate | FAIL | PASS | PASS |

| ID sai ban đầu | Keyword thiếu | Sửa |
|---|---|---|
| security-02 | token, hết hạn, chữ ký | Thêm tài liệu phân biệt API key với JWT, chữ ký và expiry |
| scaling-03 | cpu, memory, custom metrics | Thêm tài liệu HPA/autoscaling theo resource và custom metrics |

Sửa KNOWLEDGE_BASE ở develop và đồng bộ production; không sửa golden dataset.
Kết quả cuối: 23/23, regression=[].
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
p95=291.87 ms và avg=224.97 ms.
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
| A: MOCK_ERROR_RATE=0.2 | AgentHighErrorRate | 114.2 s |
| D: docker pause một trong hai instance | AgentInstanceDown | 43.9 s |

Unit test rule bằng promtool: SUCCESS, [output](evidence/part7/alert-rule-tests.txt).
[Lịch sử API alert và timestamp](evidence/part7/alert-experiments.json) chứng minh cùng thời điểm hai alert firing.
B/C không thực hiện như các thí nghiệm độc lập; không ghi số giả cho các hàng này.
Trong đợt quan sát còn có LLMCostBurnRateHigh firing tạm thời, nhưng không dùng để thay thế hai thí nghiệm A/D.

Pause giữ container trong Docker DNS nên Prometheus còn target và thấy up=0; stop có thể làm target biến mất.
Các lỗi 504 ở Nginx chưa được agent xử lý xong nên metric riêng của agent không đếm hết lỗi người dùng thấy.
Sau thí nghiệm đã unpause và khôi phục MOCK_ERROR_RATE=0.01/MOCK_SLOW_RATE=0.03 trước benchmark scaling.
Đổi sang v1 có thể làm quality giảm mà metrics hạ tầng vẫn xanh: cần eval định kỳ, quality gate và giám sát chất lượng câu trả lời.

### 4.3 Debug bằng trace

- Trace chậm: `4cb9c22e0d902c9d630c59c1f31929f1`.
- Tổng thời gian: 1856.213 ms.
- Bước xử lý chậm nhất: `chat mock-llm-small`, 1653.034 ms,
  chiếm 89.05% tổng trace. Đây là span thao tác; POST /ask và agent.run là span bao ngoài.
- Trace lỗi: `d9bdc9c11bea12e8237cfe38be75d9dc`, span chat có event exception LLMError/upstream 503.
- JSON log thật cùng trace_id, lấy trước khi recreate container:

```json
{"ts": "2026-11-25T08:34:45.101848+00:00", "level": "INFO", "service": "observable-agent", "instance": "ec23a089679f", "event": "llm_call", "trace_id": "4cb9c22e0d902c9d630c59c1f31929f1", "span_id": "c072e44f7a6b1422", "request_id": "0be7a4bfa8d2", "model": "mock-llm-small", "agent_version": "v2", "input_tokens": 73, "output_tokens": 35, "cost_usd": 3.2e-05, "llm_ms": 1652.9}
```

```json
{"ts": "2026-11-25T08:34:41.883966+00:00", "level": "INFO", "service": "observable-agent", "instance": "ec23a089679f", "event": "llm_error", "trace_id": "d9bdc9c11bea12e8237cfe38be75d9dc", "span_id": "a88a3534f4c82b6d", "request_id": "28642e04ccea", "error": "Upstream LLM error: 503 Service Unavailable (mock)"}
```

[Trace export](evidence/part7/selected-traces.json), [log liên kết](evidence/part7/trace-logs.json).
Script thu trace dùng API v3 của Jaeger 2.23 theo [API chính thức](https://www.jaegertracing.io/docs/2.23/architecture/apis/).

## 5. Benchmark scaling — Locust headless

100 user, ramp-up 10 user/s, 2 phút mỗi lượt; cùng fault mặc định và cùng model/version.
Chờ Docker DNS cập nhật 15 giây sau khi scale. Bảng dưới dùng dòng Aggregated gồm /ask và /health.
Muốn phân tích riêng nghiệp vụ cần đối chiếu dòng /ask trong CSV.

| Instance | RPS | p50 ms | p95 ms | p99 ms | Failures / Requests |
|---|---|---|---|---|---|
| 1 | 64.04 | 200 | 740 | 1700 | 83/7637 |
| 3 | 65.76 | 190 | 240 | 1700 | 75/7839 |

RPS ratio 3/1 = 1.027.
Trong lần đo này, p95 giảm từ 740 ms xuống 240 ms,
tương đương 67.57%; p99 vẫn là
1700 ms nên tail latency của mock LLM vẫn còn.
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
