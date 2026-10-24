# Existing Lab API service checkpoint

The adjacent unit and two drop-ins are exact copies of the effective existing
Lab service definitions at local commit closure. No service was restarted or
changed by capturing them. Production and Demo units are separate.

The unit preserves the Lab-only working directory/venv, loopback 18096, Lab data
root, shared fixed model target, filesystem sandbox and existing foreground
publisher. The drop-ins preserve the existing Web MVP and single-store Vision
flags. They contain no credentials or user data. Actual secrets, caches and data
are not committed. Do not run systemctl enable/restart as part of Git closure.

The deployed inference-resize file is from commit `98ae271`. Runtime dependency
Pillow 12.3.0 was already installed; the companion Lab dependency checkpoint
records that requirement without installing or upgrading anything.

---

## Persistent Lab personality selection

`85-personality-profile.conf.example` records the non-secret selection already
installed in Lab and verified at source closeout. It is an opt-in operator
sample, not an automatically installed default. The module still defaults OFF.
It does not contain P0.2 experimental prompts. Profile 0.1.1 has an empty
expression section and reuses PERS-A; P0.2 naturalness BLOCK remains valid.

The ordinary route is Open WebUI Corvus Pipe -> Lab `/api/chat` ->
`process_turn()` -> `compile_personality_system_prompt()`. Arena freezes the
same compiled instructions for main and Shadow. Source and profile are in
P0.4 `b99a5d5`, included by Voice seal `2bdd7ff`.

## Future installation or recovery (separate operational authorization)

Before editing, verify the unit is **corvus-lab-api.service**, its WorkingDirectory
is `/home/ethan/srv/apps/corvus-lab`, required profile files exist, and no other
operator is changing it. Preserve the complete existing drop-in and directory
metadata in a private recovery packet, including whether this file was absent.
Check all other drop-ins and EnvironmentFiles for conflicting selections.
Never copy this selection to Production or Demo.

From the reviewed repository root, after that preflight:

```sh
sudo install -d -o root -g root -m 0755 /etc/systemd/system/corvus-lab-api.service.d
sudo install -o root -g root -m 0644 deploy/systemd/corvus-lab-api.service.d/85-personality-profile.conf.example /etc/systemd/system/corvus-lab-api.service.d/85-personality-profile.conf
sudo systemctl daemon-reload
sudo systemctl restart corvus-lab-api.service
systemctl is-active corvus-lab-api.service
curl --fail --silent http://127.0.0.1:18096/api/health
```

These commands are documentation, not executed by source closeout. Inspect only
the three `CORVUS_PERSONALITY_*` variables in the actual MainPID environment;
never dump an entire environment containing credentials. Verify exact 0.1.1
assembly, PERS-A/safety prefix preservation and a separately authorized synthetic
normal chat. A healthy process alone does not prove which prompt was sent.

## Restore original PERS-A

Use the preserved private `restore-pers-a.sh` packet if available and its guards
still match. Otherwise restore the prior file from the private backup. If the
recorded original state was **no 85 file**, compare the installed file with this
sample first (`cmp`), then move only that file to a private backup outside the
`.conf` directory. Do not remove or modify other drop-ins. Run daemon-reload,
restart **only Lab API**, verify the actual three-variable selection is absent
or FALSE and recheck health. If any other config enables a profile, stop rather
than assume removing 85 disables it. Explicit FALSE also selects legacy PERS-A.
No database, model, TTS, Thinking or memory setting changes are needed.
