# Firebase retirement runbook

This runbook governs the staged transition from Firebase authentication to
Yarba-owned password, OAuth, access-token, and refresh-session handling.
Firebase remains enabled until the final disable criteria are met.

The reconciliation report contains Mongo user IDs, Firebase UIDs, and email
addresses. Treat it as sensitive user data: store it in an access-controlled
operator location, do not commit it, and delete it according to the incident
and migration evidence-retention policy. The repository ignores `artifacts/`
to reduce accidental commits, but filesystem permissions remain the operator's
responsibility.

## Safety invariants

- Reconciliation matches only exact `User.firebase_uid == Firebase uid`.
- Email is audit evidence only. It is never an identity-linking key.
- Google identity subjects come only from Firebase `provider_data` entries
  where `provider_id == "google.com"`; the provider entry `uid` is the subject.
  Firebase UID and email are never substituted.
- Existing Mongo user IDs and application data are preserved.
- Firebase password hashes are never exported, converted, or imported.
- The CLI is dry-run unless `--apply` is present.
- Reset email delivery additionally requires `--send-reset-emails`.
- Any preflight conflict blocks all planned database mutations.
- Do not run two apply jobs concurrently.

## Phase 0: prepare and back up

- [ ] Confirm `feat/firebase-retirement` changes passed tests in the release
      candidate.
- [ ] Export a timestamped MongoDB backup and test restoration in a non-production
      environment.
- [ ] Export Firebase Authentication users using approved Firebase tooling as
      independent rollback evidence. Do not place exports in this repository.
- [ ] Record current Firebase project ID, authorized domains, frontend deployment,
      backend deployment, and active user count.
- [ ] Restrict the planned JSON report directory to migration operators.
- [ ] Confirm no other reconciliation or account-linking job is running.

## Phase 1: deploy schema with flags off

Deploy the auth persistence migration and backend while retaining:

```env
FEATURES__ENABLE_FIREBASE_AUTH=true
FEATURES__ENABLE_NATIVE_AUTH=false
```

Keep frontend native flows disabled:

```env
VITE_NATIVE_AUTH=false
VITE_NATIVE_OAUTH=false
```

- [ ] Run database migrations.
- [ ] Verify `auth_identities`, `refresh_token_sessions`, `auth_action_tokens`,
      and `oauth_nonces` collections and indexes exist.
- [ ] Verify legacy Firebase registration/login still works.
- [ ] Verify no direct OAuth controls are visible.

## Phase 2: dry-run and review

The CLI loads normal backend environment configuration. It uses Firebase Admin
SDK pagination and the configured MongoDB database. Never paste credentials into
the command line.

```bash
uv run python scripts/reconcile_firebase_identities.py \
  --report ./artifacts/firebase-reconcile-dry-run.json
```

Dry-run is the default. Do not add `--apply` during review.

- [ ] Confirm the report says `"mode": "dry-run"`.
- [ ] Confirm every expected legacy account is matched by Firebase UID.
- [ ] Review `missing_mongo_user` and `missing_firebase_record` entries.
- [ ] Resolve every conflict, including duplicate/missing Firebase UIDs, email
      mismatches, malformed Google subjects, and identities linked to another user.
- [ ] Audit `password_only_users_needing_reset` separately.
- [ ] Confirm Google identity subjects resemble provider UIDs, not emails or
      Firebase UIDs.
- [ ] Confirm the report contains no credentials, provider tokens, password
      hashes, action tokens, or reset links.

The command exits nonzero if conflicts or review-required missing records exist.
Missing records must be explicitly accepted or corrected by the operator.

## Phase 3: apply and reconcile

After a clean reviewed dry-run, run against the same deployment/configuration:

```bash
uv run python scripts/reconcile_firebase_identities.py \
  --report ./artifacts/firebase-reconcile-apply.json \
  --apply
```

The apply operation is idempotent for identities and safe user-field promotions.
Rerun a dry-run immediately afterward and compare counts.

Default apply is blocked before mutation when the report contains either
`missing_mongo_user` or `missing_firebase_record`. After documented operator
acceptance of every missing record, rerun with the explicit override:

```bash
uv run python scripts/reconcile_firebase_identities.py \
  --report ./artifacts/firebase-reconcile-apply-accepted-missing.json \
  --apply \
  --allow-missing-records
```

`--allow-missing-records` never permits conflicts and is rejected without
`--apply`. Confirm the JSON says `"apply_blocked": false` and `"status":
"applied"`; a blocked report must not be described as a completed apply.

- [ ] Every matched user has a `FIREBASE` identity.
- [ ] Every Firebase Google user has the expected `GOOGLE` provider subject.
- [ ] No identity points to a different Mongo user ID.
- [ ] Email verification only changed from false to true.
- [ ] Password-only users without native hashes remain `FIREBASE_ONLY`.
- [ ] Firebase plus Google, or Firebase plus native password, is `DUAL`.
- [ ] Existing `NATIVE` users were not downgraded.
- [ ] A second apply produces no duplicate identities.

If a unique-index race is reported, stop concurrent jobs, rerun dry-run, and
investigate before continuing.

## Phase 4: password reset campaign

Firebase password users set a new native password through Yarba's backend reset
flow. Password hashes are not migrated.

First review the password-only section from the apply report. Confirm Resend,
frontend reset URL, API base URL, and sender domain are configured. Then:

```bash
uv run python scripts/reconcile_firebase_identities.py \
  --report ./artifacts/firebase-reconcile-reset-campaign.json \
  --apply \
  --send-reset-emails
```

If missing records were explicitly accepted during apply and remain in the
reconciliation input, include `--allow-missing-records` again for the campaign.

`--send-reset-emails` without `--apply` is rejected. The report never includes
raw reset tokens. Identity migrations remain applied if individual email
delivery fails; each failure is recorded by exception type and causes a nonzero
exit. Because email delivery is an external side effect, do not rerun the
campaign flag blindly: review the prior report first. A normal `--apply` rerun
without the campaign flag remains idempotent.

- [ ] Delivery failures are retried only after root-cause review.
- [ ] Users complete reset through the backend-owned single-use token flow.
- [ ] Completed users receive a `PASSWORD` identity and move to `DUAL` while
      Firebase remains attached.

## Phase 5: configure direct OAuth and web security

Backend audience allowlists must exactly match first-party identifiers:

```env
OAUTH_GOOGLE_WEB_AUDIENCES=<google-web-client-id>
OAUTH_GOOGLE_IOS_AUDIENCES=<google-ios-client-id>
OAUTH_GOOGLE_ANDROID_AUDIENCES=<google-android-client-id>
OAUTH_APPLE_AUDIENCES=<apple-service-id>,<apple-app-bundle-id>
```

Record and verify:

- Google web OAuth client ID.
- Google iOS reversed client configuration and client ID.
- Google Android client ID, package name, and signing certificate fingerprints.
- Apple Services ID for web, native app bundle ID, Team ID, and configured
  return domains. ID-token verification needs no client secret.

The OAuth nonce client sequence is:

1. Call `POST /api/v1/auth/oauth/nonce/google` or `/apple` with credentials.
2. Pass the returned raw nonce to Google. For Apple pass lowercase hexadecimal
   `SHA-256(UTF-8(raw nonce))`.
3. Submit only the provider ID token (and Apple's one-time display name) to the
   OAuth exchange endpoint with credentials.

Cookie/CORS checks:

- Same-site subdomains such as `www.yarba.app` and `api.yarba.app` can use
  `SameSite=Lax`, Secure cookies, explicit credentialed CORS origins, and no
  wildcard origin. Host-only cookies remain scoped to the API host.
- Truly cross-site frontend/API deployments generally require the refresh
  cookie to use `SameSite=None; Secure`, HTTPS, credentialed CORS, and CSRF
  review. The OAuth nonce cookie intentionally remains `SameSite=Lax`; host the
  nonce/exchange flow in a same-site context rather than weakening it.
- Verify `REFRESH_COOKIE_DOMAIN`, paths, Secure settings, and reverse-proxy
  forwarding in the target environment.

## Phase 6: staged flags

1. Keep Firebase enabled and enable backend native auth for internal users:

   ```env
   FEATURES__ENABLE_FIREBASE_AUTH=true
   FEATURES__ENABLE_NATIVE_AUTH=true
   ```

2. Enable frontend password flow for an internal cohort:

   ```env
   VITE_NATIVE_AUTH=true
   VITE_NATIVE_OAUTH=false
   ```

3. Only after Google identity reconciliation and audit is clean, enable direct
   OAuth for an internal cohort:

   ```env
   VITE_NATIVE_OAUTH=true
   ```

4. Expand cohorts while monitoring login failures, linking-required conflicts,
   reset delivery, refresh rotation/reuse, and support requests.

## Rollback

- Turn off frontend native flags first.
- Set `FEATURES__ENABLE_NATIVE_AUTH=false`.
- Keep `FEATURES__ENABLE_FIREBASE_AUTH=true`.
- Do not delete identities, password hashes, or session records during an
  operational rollback; they are inert behind the flag and preserve evidence.
- Revert application deployment if necessary.
- Restore MongoDB only for confirmed data corruption, using the tested backup
  and an approved incident procedure.
- Rerun dry-run after rollback to capture reconciliation state.

## Firebase disable/delete criteria

Disable Firebase authentication only when all are true:

- [ ] Reconciliation has zero unresolved conflicts.
- [ ] All intended Google identities were populated and manually sampled.
- [ ] Password migration/reset completion meets the approved threshold.
- [ ] Native access/refresh, logout-all, reset, verification, Google, and Apple
      flows pass production smoke tests.
- [ ] Frontend Firebase code paths are unused for the full observation window.
- [ ] Rollback evidence and customer support procedures are approved.
- [ ] App Store account-deletion requirements are independently satisfied.

Delete Firebase users/project configuration only after a separate retention and
security review, a longer no-rollback observation window, and a final backup.
Removing Firebase SDK/code is a later change and is not part of reconciliation.
