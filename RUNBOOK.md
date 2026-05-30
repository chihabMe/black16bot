# Black16Bot Runbook

Operational commands for maintaining the production bot.

## Server

- VM: `black16bot-vm`
- Zone: `europe-west9-b`
- IP: `34.155.124.251`
- Domain: `chihab.online`
- Logs UI: `https://logs.chihab.online`
- Project path: `/home/user/black16bot`

## Required Production Env

Set these in `/home/user/black16bot/.env` before starting Traefik:

```env
DJANGO_ALLOWED_HOSTS=chihab.online,www.chihab.online,34.155.124.251
CSRF_TRUSTED_ORIGINS=https://chihab.online,https://www.chihab.online
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
USE_X_FORWARDED_HOST=True
TRAEFIK_ACME_EMAIL=you@example.com
DOZZLE_BASIC_AUTH=admin:GENERATED_HTPASSWD_HASH
```

Generate the Dozzle password hash on the server:

```bash
openssl passwd -apr1
```

Use the output after `admin:` in `DOZZLE_BASIC_AUTH`. If Docker Compose reports an interpolation error because of `$` characters, replace every `$` in the hash with `$$`.

## Deploy From GitHub

```bash
cd /home/user/black16bot
git fetch github
git reset --hard github/master
docker-compose build web bot payment_verifier broadcast_worker
docker-compose up -d
docker-compose exec -T web python manage.py migrate
docker-compose exec -T web python manage.py test
```

Traefik issues HTTPS certificates automatically for `chihab.online`, `www.chihab.online`, and `logs.chihab.online`. Make sure GCP firewall allows TCP `80` and `443`.

## Restart Services

```bash
docker-compose restart web
docker-compose restart bot
docker-compose restart payment_verifier
docker-compose restart broadcast_worker
docker-compose restart traefik
```

Restart everything:

```bash
docker-compose up -d
```

## Check Status

```bash
docker-compose ps
docker-compose exec -T web python manage.py check
```

## Logs

```bash
docker-compose logs -f web
docker-compose logs -f bot
docker-compose logs -f payment_verifier
docker-compose logs -f broadcast_worker
```

## Dozzle Logs UI

Dozzle is exposed through Traefik at `https://logs.chihab.online` and protected with Basic Auth.

Start it:

```bash
docker-compose up -d dozzle
```

If Dozzle does not ask for a password, stop immediately and check `DOZZLE_BASIC_AUTH` plus the Traefik labels.

## Domain And HTTPS

Verify DNS:

```bash
nslookup chihab.online 8.8.8.8
nslookup www.chihab.online 8.8.8.8
nslookup logs.chihab.online 8.8.8.8
```

Each hostname should resolve to `34.155.124.251`.

Verify HTTPS:

```bash
curl -I https://chihab.online
curl -I https://www.chihab.online
curl -I https://logs.chihab.online
```

`logs.chihab.online` should return `401 Unauthorized` before login.

## Payments

Verify pending payments manually:

```bash
docker-compose exec -T web python manage.py verify_payments --limit 100
```

Expire old pending payments:

```bash
docker-compose exec -T web python manage.py expire_payments
```

In Django Admin, select pending payment requests and run `Verify selected pending payment requests`.

## Broadcasts

Broadcasts are queued from Django Admin and sent by `broadcast_worker`.

Recover broadcasts stuck in `sending`:

```bash
docker-compose exec -T web python manage.py recover_broadcasts
```

If broadcasts are not sending:

```bash
docker-compose ps broadcast_worker
docker-compose logs -f broadcast_worker
docker-compose restart broadcast_worker
```

## Common Issues

### Bot Not Responding

```bash
docker-compose ps bot
docker-compose logs -f bot
docker-compose restart bot
```

Check that `TELEGRAM_BOT_TOKEN` is set in `.env`.

### Admin Down

```bash
docker-compose ps web
docker-compose logs -f web
docker-compose restart web
```

Check that Traefik is running, the VM firewall allows ports `80` and `443`, and `DJANGO_ALLOWED_HOSTS` includes the domain.

### Payments Not Verifying

```bash
docker-compose logs -f payment_verifier
docker-compose exec -T web python manage.py verify_payments --limit 100
```

Check Binance/API wallet keys in `.env` and confirm users submitted the correct order ID or transaction ID.

### Products Out Of Stock

Use Django Admin product `Upload stock`, then optionally notify users about fresh stock.

### Database Migrations Needed

```bash
docker-compose exec -T web python manage.py migrate
```

### Run Tests

```bash
docker-compose exec -T web python manage.py test
```
