# Deployment Information — Day 14

## Trạng thái

**Tạm bỏ deploy cloud theo yêu cầu của người học.** Toàn bộ checkpoint local đã có bằng chứng; CP6 chưa hoàn tất.
Chưa có public URL đã kiểm chứng, chưa có ba ảnh cloud `dashboard.png`, `running.png`, `test.png`.
Không dùng localhost hoặc ảnh local thay cho bằng chứng cloud.

## Nền tảng đã kiểm tra

| Nền tảng | Kết quả thực tế ngày 25/11/2026 |
|---|---|
| Railway | Đăng nhập CLI thành công. Tạo project bị từ chối: `Your trial has expired. Please select a plan to continue using Railway.` |
| Render (được chọn thay thế) | Đăng nhập CLI thành công. Validate Blueprint trả `need_payment_info`; tạo Redis với `--plan free` trả HTTP 402: `Payment information is required to complete this request.` |

Không tạo gói trả phí, không nhập thông tin thanh toán. Chủ tài khoản cần tự hoàn thành billing hoặc trao đổi Lab Coach theo RULES.md.
Không có service cloud nào được tạo thành công trong hai lần thử này.

## Cấu hình sẵn sàng

- Source: `06-lab-complete/`; Dockerfile multi-stage, non-root, dùng PORT của nền tảng.
- Render Blueprint: `06-lab-complete/render.yaml`, web + Key Value cùng region Singapore, đều khai báo plan free.
- API key dùng generateValue hoặc env, không ghi key thật trong repo.
- Redis chỉ truy cập nội bộ; REDIS_URL lấy connectionString của backing service.
- Railway config dự phòng: `06-lab-complete/railway.toml`.
- Kiểm tra local đầy đủ: [PASS 12/12](evidence/part6/readiness.txt).
- Kiểm tra HTTP/validation/concurrency Compose: [api-validation.json](evidence/part6/api-validation.json).

## Biến môi trường trên cloud

| Biến | Cách đặt |
|---|---|
| ENVIRONMENT | production |
| PORT | Do nền tảng cấp; Docker CMD đọc biến này |
| AGENT_API_KEY | Secret ngẫu nhiên, lưu ở platform; không ghi giá trị vào tài liệu |
| REDIS_URL | Connection string nội bộ của Redis/Key Value |
| RATE_LIMIT_PER_MINUTE | 10 |
| DAILY_BUDGET_USD | 1 |
| MONTHLY_BUDGET_USD | 10 |
| LOG_LEVEL | INFO |

Đây là giá trị cấu hình dự kiến; chưa khẳng định đã đặt lên service cloud khi chưa tạo được service.
Redis free không bảo đảm persistence qua restart datastore; state vẫn dùng chung và còn sau restart agent.
Giới hạn thực hành này khác Redis AOF trong Compose local.

## Tiếp tục deploy Render khi tài khoản sẵn sàng

1. Push bản bài làm lên fork GitHub.
2. Trong Render tạo Blueprint từ repo, chọn đường dẫn `06-lab-complete/render.yaml`.
3. Kiểm tra web service và Key Value đều plan free, region Singapore; không nâng plan tự động.
4. Deploy, chờ `/ready` thực sự trả 200 (không chỉ nhìn healthcheck nền tảng).
5. Chạy bốn lệnh bên dưới; lưu mã HTTP và ba ảnh cloud, rồi cập nhật trạng thái file này.

Tham khảo [Render CLI](https://render.com/docs/cli), [Blueprint spec](https://render.com/docs/blueprint-spec).

## Bốn kiểm tra public bắt buộc

Các lệnh này là quy trình sau deploy, **chưa phải output cloud đã chạy**. Đặt BASE bằng URL service và AGENT_API_KEY bằng secret trong shell riêng.

```bash
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"  # 200
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"   # 200
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" \
  -H 'Content-Type: application/json' -d '{"question":"Hello"}'  # 401
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" \
  -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" \
  -d '{"question":"Hello"}'  # 200
```

## Ảnh cần bổ sung sau deploy

- `screenshots/dashboard.png`: dashboard nền tảng và trạng thái deploy.
- `screenshots/running.png`: service cloud đang chạy.
- `screenshots/test.png`: bốn kết quả HTTP, không hiển thị key/token.

Bốn ảnh observability thực tế đã có trong `screenshots/`; không thay thế ba ảnh cloud còn thiếu.
