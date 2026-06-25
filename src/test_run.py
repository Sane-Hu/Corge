import sys
from pathlib import Path
from corge.__main__ import RealCorgeApp

target_path = Path("/home/sane/1-MY_DATA/Projects/AAI_NTI/Corge_PLAN/Corge").resolve()
global_dir = Path.home() / ".config" / "corge"
config_path = target_path / "CorgeAPIConfig.toml"

app = RealCorgeApp(target_repo=target_path, config_path=config_path, global_dir=global_dir)
app.run()
