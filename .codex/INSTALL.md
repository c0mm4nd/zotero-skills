# Install
1. Clone the repo.
2. Link the skills folder into your Codex skills directory:

```bash
ln -s "$(pwd)/zotero-skills/skills" "$HOME/.agents/skills/zotero-skills"
```

3. Restart Codex so it re-scans skills.

# Uninstall
1. Remove the symlink:

```bash
rm "$HOME/.agents/skills/zotero-skills"
```
