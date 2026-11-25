# Deployment Information — Day 14

## Public URL

[Agent trên Railway](https://day14-agent-production-a76b55eb.up.railway.app) · [Swagger API](https://day14-agent-production-a76b55eb.up.railway.app/docs)

**Hoàn tất CP6:** agent Part 6 và Redis đã deploy thành công bằng tài khoản Railway mới.
Bốn kiểm tra public được chạy ngày 25/11/2026 lúc 16:33 (GMT+7), kết quả **200 / 200 / 401 / 200**.

## Platform và cấu hình thực tế

- Platform: Railway, environment production, project `k5-day14-agent-lab`.
- [Project Railway](https://railway.com/project/2b15432f-a698-4d06-ac54-783627508e3e) (cần tài khoản có quyền truy cập).
- Service `day14-agent`: SUCCESS, deployment `da360dea-a687-457f-a340-1775ef43eb40`, một replica, hai Uvicorn worker.
- Service `Redis`: SUCCESS, Redis 8.2, một replica, volume `/data` 500 MB.
- Agent kết nối `redis.railway.internal:6379`, có authentication; không ghi URL chứa mật khẩu vào tài liệu.
- Source upload từ `06-lab-complete/`; builder DOCKERFILE, healthcheckPath `/health`, port 8000.
- Deploy bằng `railway up . --path-as-root --service day14-agent --detach`; chưa cấu hình GitHub autodeploy.
- App mock LLM, không sử dụng API key LLM thật.

Dữ liệu trực tiếp từ Railway: [railway-deployment.json](evidence/part6/railway-deployment.json).
Kiểm tra local đầy đủ trước deploy: [PASS 12/12, 43/43 checks](evidence/part6/readiness.txt).

## Kết quả kiểm tra public

| Request | API key | HTTP thực tế |
|---|---|---:|
| GET /health | Không cần | 200 |
| GET /ready | Không cần | 200 |
| POST /ask | Thiếu | 401 |
| POST /ask | Đúng | 200 |

[Request/response thực tế](evidence/part6/public-api.json); `ready=true` xác nhận agent kết nối được Redis.
Request có key trả câu trả lời mock: “Deployment là quá trình đưa code từ máy bạn lên server để người khác dùng được.”

## Environment variables đã đặt trên Railway

| Biến | Cách đặt / giá trị không nhạy cảm |
|---|---|
| ENVIRONMENT | production |
| PORT | 8000; Docker CMD đọc PORT |
| AGENT_API_KEY | Key ngẫu nhiên; đặt qua Railway CLI stdin, giá trị được che |
| REDIS_URL | Tham chiếu `${{Redis.REDIS_URL}}` đến service Redis |
| RATE_LIMIT_PER_MINUTE | 10 |
| DAILY_BUDGET_USD | 1 |
| MONTHLY_BUDGET_USD | 10 |
| LOG_LEVEL | INFO |

Thông tin gọi API được lưu riêng trên máy trong `06-lab-complete/.env.production` (đã ignore, không commit).
Không ghi API key, password Redis hoặc token đăng nhập vào báo cáo/ảnh/Git.

## Lệnh tự kiểm tra

Trong Bash, đặt `BASE` thành URL public và `AGENT_API_KEY` thành secret của service trong shell riêng:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"  # 200
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"   # 200
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" \
  -H 'Content-Type: application/json' -d '{"question":"Hello"}'  # 401
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" \
  -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" \
  -d '{"question":"Hello"}'  # 200
```

Script kiểm tra và lưu bằng chứng: `python scripts/verify_public_deployment.py --url "$BASE"`.
Script đọc key qua environment và không ghi credential vào output.

## Screenshots

- [Trạng thái deploy](screenshots/dashboard.png): bản xuất trạng thái Railway CLI từ JSON thật; không phải ảnh giao diện web Railway đã đăng nhập.
- [Service đang chạy](screenshots/running.png): Swagger UI tải trực tiếp từ URL public.
- [Kết quả test](screenshots/test.png): bản xuất bốn response HTTP thật, đã che key.

Công cụ browser/native host không kết nối được, nên ảnh trạng thái và test được render bằng Chromium từ bằng chứng CLI/HTTP,
được ghi nguồn rõ ràng; không dựng lại giao diện Railway hoặc tự tạo số liệu.

## Lịch sử xử lý tài khoản

Các lần thử bằng tài khoản trước bị giới hạn Railway trial và Render billing, xem [cloud-attempts.json](evidence/part6/cloud-attempts.json).
Sau khi người học đăng nhập tài khoản Railway khác, project/Redis/agent đã tạo và deploy thành công.
Không thực hiện nâng gói trả phí hoặc nhập thông tin thanh toán trong quá trình này.
