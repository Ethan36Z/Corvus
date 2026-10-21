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
