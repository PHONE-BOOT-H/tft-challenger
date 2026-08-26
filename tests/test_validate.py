import pytest

from src.validate import ClusterMismatch, SetMismatch, check_set, pin_cluster


def _payloads(cluster_set="TFTSet18", early_set="TFTSet18", cluster_id=410, data_id=410):
    return {
        "latest_cluster_id": {"tft_set": cluster_set, "cluster_id": cluster_id},
        "comps_data": {"tft_set": cluster_set, "cluster_id": data_id},
        "early": {"tft_set": early_set},
    }


def test_셋이_맞으면_통과한다():
    check_set(_payloads(), expected="TFTSet18")


def test_집계가_지난_셋이면_거부한다():
    with pytest.raises(SetMismatch) as err:
        check_set(_payloads(cluster_set="TFTSet17"), expected="TFTSet18")
    assert "TFTSet17" in str(err.value)


def test_early만_지난_셋이어도_거부한다():
    with pytest.raises(SetMismatch) as err:
        check_set(_payloads(early_set="TFTSet17"), expected="TFTSet18")
    assert "early" in str(err.value)


def test_셋_필드가_없으면_거부한다():
    payloads = _payloads()
    del payloads["early"]["tft_set"]
    with pytest.raises(SetMismatch):
        check_set(payloads, expected="TFTSet18")


def test_cluster_id가_맞으면_그_값을_돌려준다():
    assert pin_cluster(_payloads(cluster_id=410, data_id=410)) == 410


def test_cluster_id가_어긋나면_거부한다():
    with pytest.raises(ClusterMismatch):
        pin_cluster(_payloads(cluster_id=410, data_id=409))
