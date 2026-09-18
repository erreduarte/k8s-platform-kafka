# Public mirror sanitization

This repository preserves the private project's domains, automation structure,
tests, workflows, and documentation. Sanitization changes values, not the
architecture:

- private hosts use `example.invalid` names;
- private RFC1918 addresses use documentation ranges such as `192.0.2.0/24`;
- cloud accounts, buckets, backends, VM identifiers, and repository owners use
  neutral examples;
- credentials remain represented by environment variables, GitHub Secrets,
  Ansible variables, or Kubernetes Secret references;
- the self-hosted runner labels and deployment workflows remain as examples,
  but no runner, endpoint, or secret value is included;
- the SSH public-key file is retained as a placeholder so the bootstrap flow
  can be configured with a user's own key;
- Git history from the private repository is not copied.

Before deploying, replace the example inventory and secret values in a private
configuration layer. Do not commit the replacements to this repository.