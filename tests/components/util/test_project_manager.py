# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean CLI v1.0. Copyright 2021 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from unittest import mock

import pytest
from lxml import etree

from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.config.storage import Storage
from lean.components.util.path_manager import PathManager
from lean.components.util.platform_manager import PlatformManager
from lean.components.util.project_manager import ProjectManager
from lean.components.util.xml_manager import XMLManager
from lean.models.api import QCLanguage
from tests.test_helpers import create_fake_lean_cli_directory


def _create_project_manager() -> ProjectManager:
    logger = mock.Mock()
    xml_manager = XMLManager()
    project_config_manager = ProjectConfigManager(xml_manager)
    cache_storage = Storage(str(Path("~/.lean/cache").expanduser()))
    platform_manager = PlatformManager()
    path_manager = PathManager(platform_manager)

    return ProjectManager(logger,
                          project_config_manager,
                          LeanConfigManager(mock.Mock(),
                                            mock.Mock(),
                                            project_config_manager,
                                            mock.Mock(),
                                            cache_storage),
                          path_manager,
                          xml_manager,
                          platform_manager)


def test_find_algorithm_file_returns_input_when_input_is_file() -> None:
    create_fake_lean_cli_directory()

    project_manager = _create_project_manager()
    result = project_manager.find_algorithm_file(Path.cwd() / "Python Project" / "main.py")

    assert result == Path.cwd() / "Python Project" / "main.py"


def test_find_algorithm_file_returns_main_py_when_input_directory_contains_it() -> None:
    create_fake_lean_cli_directory()

    project_manager = _create_project_manager()
    result = project_manager.find_algorithm_file(Path.cwd() / "Python Project")

    assert result == Path.cwd() / "Python Project" / "main.py"


def test_find_algorithm_file_returns_main_cs_when_input_directory_contains_it() -> None:
    create_fake_lean_cli_directory()

    project_manager = _create_project_manager()
    result = project_manager.find_algorithm_file(Path.cwd() / "CSharp Project")

    assert result == Path.cwd() / "CSharp Project" / "Main.cs"


def test_find_algorithm_file_raises_error_when_no_algorithm_file_exists() -> None:
    create_fake_lean_cli_directory()

    (Path.cwd() / "Empty Project").mkdir()

    project_manager = _create_project_manager()

    with pytest.raises(Exception):
        project_manager.find_algorithm_file(Path.cwd() / "Empty Project")


def test_get_project_by_id_returns_path_to_project() -> None:
    create_fake_lean_cli_directory()

    project_dir = Path.cwd() / "Python Project"

    project_config_manager = ProjectConfigManager(XMLManager())
    project_id = project_config_manager.get_local_id(project_dir)

    project_manager = _create_project_manager()

    assert project_manager.get_project_by_id(project_id) == project_dir


def test_get_project_by_id_raises_error_when_no_project_with_given_id_exists() -> None:
    create_fake_lean_cli_directory()

    project_config_manager = ProjectConfigManager(XMLManager())
    python_project_id = project_config_manager.get_local_id(Path.cwd() / "Python Project")
    csharp_project_id = project_config_manager.get_local_id(Path.cwd() / "CSharp Project")

    project_manager = _create_project_manager()

    with pytest.raises(Exception):
        project_manager.get_project_by_id(max(python_project_id, csharp_project_id) + 1)


def test_get_source_files_returns_all_source_files() -> None:
    project_path = Path.cwd() / "My Project"
    project_path.mkdir()

    files = ["Main.cs", "main.py", "research.ipynb", "path/to/Alpha.cs", "path/to/alpha.py"]
    files = [project_path / file for file in files]

    for file in files:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.touch()

    project_manager = _create_project_manager()
    files_to_sync = project_manager.get_source_files(project_path)

    assert sorted(files_to_sync) == sorted(files)


@pytest.mark.parametrize("directory", ["bin", "obj", ".ipynb_checkpoints", "backtests", "live", "optimizations"])
def test_get_source_files_ignores_generated_source_files(directory: str) -> None:
    project_path = Path.cwd() / "My Project"
    project_path.mkdir()

    files = [project_path / "main.py", project_path / directory / "main.py"]
    for file in files:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.touch()

    project_manager = _create_project_manager()
    files_to_sync = project_manager.get_source_files(project_path)

    assert files_to_sync == [files[0]]


def test_update_last_modified_time_updates_file_properties() -> None:
    local_file = Path.cwd() / "file.txt"
    local_file.touch()

    new_timestamp = datetime(2020, 1, 1, 1, 1, 1)

    project_manager = _create_project_manager()
    project_manager.update_last_modified_time(local_file, new_timestamp)

    timestamp = local_file.stat().st_mtime_ns / 1e9
    timestamp = datetime.fromtimestamp(timestamp)
    assert timestamp.astimezone(tz=timezone.utc).replace(tzinfo=None) == new_timestamp


def test_copy_code_copies_source_files_to_output_directory() -> None:
    project_path = Path.cwd() / "My Project"
    project_path.mkdir()

    files = ["Main.cs", "main.py", "research.ipynb", "path/to/Alpha.cs", "path/to/alpha.py"]
    files = [project_path / file for file in files]

    output_dir = Path.cwd() / "code"

    for file in files:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.touch()
        file.write_text(file.name, encoding="utf-8")

    project_manager = _create_project_manager()
    project_manager.copy_code(project_path, output_dir)

    for file in files:
        assert (output_dir / file).is_file()
        assert (output_dir / file).read_text(encoding="utf-8") == file.name


@pytest.mark.parametrize("directory", ["bin", "obj", ".ipynb_checkpoints", "backtests", "live", "optimizations"])
def test_copy_code_ignores_generated_source_files(directory: str) -> None:
    project_path = Path.cwd() / "My Project"
    project_path.mkdir()

    files = [project_path / "main.py", project_path / directory / "main.py"]
    for file in files:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.touch()
        file.write_text(file.name, encoding="utf-8")

    output_dir = Path.cwd() / "code"

    project_manager = _create_project_manager()
    project_manager.copy_code(project_path, output_dir)

    assert (output_dir / "main.py").is_file()
    assert (output_dir / "main.py").read_text(encoding="utf-8") == "main.py"

    assert not (output_dir / directory / "main.py").is_file()


def test_create_new_project_creates_project_directory() -> None:
    project_path = Path.cwd() / "Python Project"

    project_manager = _create_project_manager()
    project_manager.create_new_project(project_path, QCLanguage.Python)

    assert project_path.is_dir()


@pytest.mark.parametrize("language", [QCLanguage.Python, QCLanguage.CSharp])
def test_create_new_project_sets_language_in_project_config(language: QCLanguage) -> None:
    project_path = Path.cwd() / f"{language.name} Project"

    project_manager = _create_project_manager()
    project_manager.create_new_project(project_path, language)

    config = Storage(str(project_path / "config.json"))

    assert config.get("algorithm-language") == language.name


def test_create_new_project_sets_parameters_in_project_config() -> None:
    project_path = Path.cwd() / "Python Project"

    project_manager = _create_project_manager()
    project_manager.create_new_project(project_path, QCLanguage.Python)

    config = Storage(str(project_path / "config.json"))

    assert config.get("parameters") == {}


def test_create_new_project_sets_description_in_project_config() -> None:
    project_path = Path.cwd() / "Python Project"

    project_manager = _create_project_manager()
    project_manager.create_new_project(project_path, QCLanguage.Python)

    config = Storage(str(project_path / "config.json"))

    assert config.get("description") == ""


def validate_json(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except ValueError:
        return False


def validate_xml(text: str) -> bool:
    try:
        XMLManager().parse(text)
        return True
    except etree.ParseError:
        return False


@pytest.mark.parametrize("file,validator", [(".vscode/launch.json", validate_json),
                                            (".vscode/settings.json", validate_json),
                                            (".idea/Python Project.iml", validate_xml),
                                            (".idea/misc.xml", validate_xml),
                                            (".idea/modules.xml", validate_xml),
                                            (".idea/workspace.xml", validate_xml)])
def test_create_new_project_creates_valid_python_editor_configs(file: str, validator: Callable[[str], bool]) -> None:
    project_path = Path.cwd() / "Python Project"

    project_manager = _create_project_manager()
    project_manager.create_new_project(project_path, QCLanguage.Python)

    assert (project_path / file).is_file()

    with open(project_path / file) as f:
        assert validator(f.read())


@pytest.mark.parametrize("file,validator", [("CSharp Project.csproj", validate_xml),
                                            (".vscode/launch.json", validate_json)])
def test_create_new_project_creates_valid_csharp_editor_configs(file: str, validator: Callable[[str], bool]) -> None:
    project_path = Path.cwd() / "CSharp Project"

    project_manager = _create_project_manager()
    project_manager.create_new_project(project_path, QCLanguage.CSharp)

    assert (project_path / file).is_file()

    with open(project_path / file) as f:
        assert validator(f.read())


@mock.patch("platform.system")
@pytest.mark.parametrize("editor,os,path", [("PyCharm", "Windows", "~/AppData/Roaming/JetBrains"),
                                            ("PyCharm", "Darwin", "~/Library/Application Support/JetBrains"),
                                            ("PyCharm", "Linux", "~/.config/JetBrains"),
                                            ("PyCharmCE", "Windows", "~/AppData/Roaming/JetBrains"),
                                            ("PyCharmCE", "Darwin", "~/Library/Application Support/JetBrains"),
                                            ("PyCharmCE", "Linux", "~/.config/JetBrains")])
def test_create_new_project_creates_pycharm_jdk_entry_when_not_set_yet(system: mock.Mock,
                                                                       editor: str,
                                                                       os: str,
                                                                       path: str) -> None:
    system.return_value = os

    jdk_table_file = Path(path).expanduser() / f"{editor}2020.3" / "options" / "jdk.table.xml"
    jdk_table_file.parent.mkdir(parents=True, exist_ok=True)
    with jdk_table_file.open("w+", encoding="utf-8") as file:
        file.write("""
<application>
  <component name="ProjectJdkTable">
  </component>
</application>
        """)

    project_manager = _create_project_manager()
    project_manager.create_new_project(Path.cwd() / "Python Project", QCLanguage.Python)

    jdk_table = etree.fromstring(jdk_table_file.read_text(encoding="utf-8"))
    assert jdk_table.find(".//jdk/name[@value='Lean CLI']") is not None


@mock.patch("platform.system")
@pytest.mark.parametrize("editor,os,path", [("PyCharm", "Windows", "~/AppData/Roaming/JetBrains"),
                                            ("PyCharm", "Darwin", "~/Library/Application Support/JetBrains"),
                                            ("PyCharm", "Linux", "~/.config/JetBrains"),
                                            ("PyCharmCE", "Windows", "~/AppData/Roaming/JetBrains"),
                                            ("PyCharmCE", "Darwin", "~/Library/Application Support/JetBrains"),
                                            ("PyCharmCE", "Linux", "~/.config/JetBrains")])
def test_create_new_project_creates_pycharm_jdk_entry_when_pycharm_not_installed_yet(system: mock.Mock,
                                                                                     editor: str,
                                                                                     os: str,
                                                                                     path: str) -> None:
    system.return_value = os

    project_manager = _create_project_manager()
    project_manager.create_new_project(Path.cwd() / "Python Project", QCLanguage.Python)

    jdk_table_file = Path(path).expanduser() / editor / "options" / "jdk.table.xml"
    assert jdk_table_file.is_file()

    jdk_table = etree.fromstring(jdk_table_file.read_text(encoding="utf-8"))
    assert jdk_table.find(".//jdk/name[@value='Lean CLI']") is not None


@mock.patch("platform.system")
@pytest.mark.parametrize("editor,os,path", [("PyCharm", "Windows", "~/AppData/Roaming/JetBrains"),
                                            ("PyCharm", "Darwin", "~/Library/Application Support/JetBrains"),
                                            ("PyCharm", "Linux", "~/.config/JetBrains"),
                                            ("PyCharmCE", "Windows", "~/AppData/Roaming/JetBrains"),
                                            ("PyCharmCE", "Darwin", "~/Library/Application Support/JetBrains"),
                                            ("PyCharmCE", "Linux", "~/.config/JetBrains")])
def test_create_new_project_does_not_update_pycharm_jdk_table_when_jdk_entry_already_set(system: mock.Mock,
                                                                                         editor: str,
                                                                                         os: str,
                                                                                         path: str) -> None:
    system.return_value = os

    jdk_table = """
<application>
  <component name="ProjectJdkTable">
    <jdk version="2">
      <name value="Lean CLI" />
    </jdk>
  </component>
</application>
    """

    jdk_table_file = Path(path).expanduser() / f"{editor}2020.3" / "options" / "jdk.table.xml"
    jdk_table_file.parent.mkdir(parents=True, exist_ok=True)
    with jdk_table_file.open("w+", encoding="utf-8") as file:
        file.write(jdk_table)

    project_manager = _create_project_manager()
    project_manager.create_new_project(Path.cwd() / "Python Project", QCLanguage.Python)

    assert jdk_table_file.read_text(encoding="utf-8") == jdk_table


def test_create_new_project_copies_ssh_keys_to_global_config_dir() -> None:
    project_manager = _create_project_manager()
    project_manager.create_new_project(Path.cwd() / "CSharp Project", QCLanguage.CSharp)

    for name in ["key", "key.pub", "README.md"]:
        assert Path(f"~/.lean/ssh/{name}").expanduser().is_file()


@mock.patch("platform.system")
@pytest.mark.parametrize("os,path", [("Windows", "~/AppData/Roaming/JetBrains"),
                                     ("Darwin", "~/Library/Application Support/JetBrains"),
                                     ("Linux", "~/.config/JetBrains")])
def test_create_new_project_creates_rider_debugger_entry_when_not_set_yet(system: mock.Mock,
                                                                          os: str,
                                                                          path: str) -> None:
    system.return_value = os

    key_path = Path("~/.lean/ssh/key").expanduser()

    debugger_file = Path(path).expanduser() / "Rider" / "options" / "debugger.xml"
    debugger_file.parent.mkdir(parents=True, exist_ok=True)
    with debugger_file.open("w+", encoding="utf-8") as file:
        file.write(f"""
<application>
  <component name="XDebuggerSettings">
    <data-views />
    <general />
    <debuggers>
      <debugger id="dotnet_debugger">
        <configuration>
          <option name="needNotifyWhenStoppedInExternalCode" value="false" />
          <option name="sshCredentials">
            <option value="&lt;credentials HOST=&quot;localhost&quot; PORT=&quot;2222&quot; USERNAME=&quot;root&quot; PRIVATE_KEY_FILE=&quot;{key_path.as_posix()}&quot; USE_KEY_PAIR=&quot;true&quot; USE_AUTH_AGENT=&quot;false&quot; /&gt;" />
          </option>
        </configuration>
      </debugger>
    </debuggers>
  </component>
</application>
        """)

    project_manager = _create_project_manager()
    project_manager.create_new_project(Path.cwd() / "CSharp Project", QCLanguage.CSharp)

    debugger_root = XMLManager().parse(debugger_file.read_text(encoding="utf-8"))
    assert debugger_root.find(
        f".//option/option[@value='<credentials HOST=\"localhost\" PORT=\"2222\" USERNAME=\"root\" PRIVATE_KEY_FILE=\"{key_path.as_posix()}\" USE_KEY_PAIR=\"true\" USE_AUTH_AGENT=\"false\" />']") is not None


@mock.patch("platform.system")
@pytest.mark.parametrize("os,path", [("Windows", "~/AppData/Roaming/JetBrains"),
                                     ("Darwin", "~/Library/Application Support/JetBrains"),
                                     ("Linux", "~/.config/JetBrains")])
def test_create_new_project_creates_rider_debugger_config_when_rider_not_installed_yet(system: mock.Mock,
                                                                                       os: str,
                                                                                       path: str) -> None:
    system.return_value = os

    key_path = Path("~/.lean/ssh/key").expanduser()

    project_manager = _create_project_manager()
    project_manager.create_new_project(Path.cwd() / "CSharp Project", QCLanguage.CSharp)

    debugger_file = Path(path).expanduser() / "Rider" / "options" / "debugger.xml"
    assert debugger_file.is_file()

    debugger_root = XMLManager().parse(debugger_file.read_text(encoding="utf-8"))
    assert debugger_root.find(
        f".//option/option[@value='<credentials HOST=\"localhost\" PORT=\"2222\" USERNAME=\"root\" PRIVATE_KEY_FILE=\"{key_path.as_posix()}\" USE_KEY_PAIR=\"true\" USE_AUTH_AGENT=\"false\" />']") is not None


@mock.patch("platform.system")
@pytest.mark.parametrize("editor,os,path", [("PyCharm", "Windows", "~/AppData/Roaming/JetBrains"),
                                            ("PyCharm", "Darwin", "~/Library/Application Support/JetBrains"),
                                            ("PyCharm", "Linux", "~/.config/JetBrains"),
                                            ("PyCharmCE", "Windows", "~/AppData/Roaming/JetBrains"),
                                            ("PyCharmCE", "Darwin", "~/Library/Application Support/JetBrains"),
                                            ("PyCharmCE", "Linux", "~/.config/JetBrains")])
def test_create_new_project_does_not_update_rider_debugger_config_when_entry_already_set(system: mock.Mock,
                                                                                         editor: str,
                                                                                         os: str,
                                                                                         path: str) -> None:
    system.return_value = os

    key_path = Path("~/.lean/ssh/key").expanduser()

    debugger_content = f"""
<application>
  <component name="XDebuggerSettings">
    <data-views />
    <general />
    <debuggers>
      <debugger id="dotnet_debugger">
        <configuration>
          <option name="needNotifyWhenStoppedInExternalCode" value="false" />
          <option name="sshCredentials">
            <option value="&lt;credentials HOST=&quot;localhost&quot; PORT=&quot;2222&quot; USERNAME=&quot;root&quot; PRIVATE_KEY_FILE=&quot;{key_path.as_posix()}&quot; USE_KEY_PAIR=&quot;true&quot; USE_AUTH_AGENT=&quot;false&quot; /&gt;" />
          </option>
        </configuration>
      </debugger>
    </debuggers>
  </component>
</application>
    """

    debugger_file = Path(path).expanduser() / "Rider" / "options" / "debugger.xml"
    debugger_file.parent.mkdir(parents=True, exist_ok=True)
    with debugger_file.open("w+", encoding="utf-8") as file:
        file.write(debugger_content)

    project_manager = _create_project_manager()
    project_manager.create_new_project(Path.cwd() / "CSharp Project", QCLanguage.CSharp)

    assert debugger_file.read_text(encoding="utf-8") == debugger_content
