# Install
1. Clone/update the repo in a fixed location and link the skills folder into your Codex skills directory:

```bash
mkdir -p "$HOME/.agents/repos" "$HOME/.agents/skills"
if [ -d "$HOME/.agents/repos/zotero-skills/.git" ]; then
  git -C "$HOME/.agents/repos/zotero-skills" pull --ff-only
else
  git clone https://github.com/c0mm4nd/zotero-skills "$HOME/.agents/repos/zotero-skills"
fi
rm -f "$HOME/.agents/skills/zotero-skills"
ln -s "$HOME/.agents/repos/zotero-skills/skills" "$HOME/.agents/skills/zotero-skills"
```

2. Configure Zotero Web API credentials (stored in plaintext in `skills/zotero-library/SKILL.md`):

```bash
python3 "$HOME/.agents/repos/zotero-skills/skills/zotero-library/scripts/configure_web_api_credentials.py"
```

3. Restart Codex so it re-scans skills.

# Uninstall
1. Remove the symlink:

```bash
rm -f "$HOME/.agents/skills/zotero-skills"
```

2. Optional: remove the local clone:

```bash
rm -rf "$HOME/.agents/repos/zotero-skills"
```

3. Restart Codex so it re-scans skills.
