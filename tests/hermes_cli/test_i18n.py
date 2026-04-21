from unittest.mock import patch

from hermes_cli.i18n import t


def test_pending_force_stop_translation_exists_in_supported_locales():
    with patch("hermes_cli.i18n._base.get_locale", return_value="en"):
        assert t("gateway.stop.force_stopped") != "gateway.stop.force_stopped"

    with patch("hermes_cli.i18n._base.get_locale", return_value="zh"):
        assert t("gateway.stop.force_stopped") != "gateway.stop.force_stopped"
