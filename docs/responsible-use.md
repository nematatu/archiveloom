# Responsible use

ArchiveLoom is a preservation and workflow tool, not an access-control bypass.

## Appropriate uses

- Content you created or own
- Content whose owner gave you permission to download
- Public-domain or openly licensed media
- Institutional backups performed under an applicable agreement
- Public archives where automated download is allowed by the service and applicable law

## Unsupported uses

- Circumventing DRM, paywalls, passwords, CAPTCHA, MFA, or access controls
- Obtaining private or restricted media without authorization
- Evading rate limits or service blocks
- Redistributing content without the necessary rights
- Hiding automated traffic or impersonating another person

## Adapter requirements

Every contributed site adapter must document:

- The supported public URL patterns
- Whether authentication is required
- Which official or browser-used interfaces it relies on
- Rate-limit behavior and bounded retries
- Known unsupported or DRM-protected flows
- A fixture that contains no credentials or signed URLs

Maintainers may reject or remove adapters that create disproportionate legal, security, privacy, or operational risk.

## No legal conclusion

ArchiveLoom cannot determine whether a particular download is lawful in every jurisdiction or contract. Users and adapter authors are responsible for confirming authorization and applicable terms.
