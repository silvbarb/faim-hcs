# SPDX-FileCopyrightText: 2023 Friedrich Miescher Institute for Biomedical Research (FMI), Basel (Switzerland)
#
# SPDX-License-Identifier: BSD-3-Clause

from pathlib import Path

import numpy as np
import pytest

from faim_hcs.io.MolecularDevicesImageXpress import parse_files
from faim_hcs.MetaSeriesUtils import (
    _stage_label,
    get_well_image_CYX,
    get_well_image_CZYX,
    montage_grid_image_YX,
    montage_stage_pos_image_YX,
)

ROOT_DIR = Path(__file__).parent.parent


@pytest.fixture
def files():
    return parse_files(ROOT_DIR / "resources" / "Projection-Mix")


def test_get_well_image_CYX(files):
    files2d = files[(files["z"].isnull()) & (files["channel"].isin(["w1", "w2"]))]
    for well in files2d["well"].unique():
        img, hists, ch_metadata, metadata, roi_tables = get_well_image_CYX(
            files2d[files2d["well"] == well],
            channels=["w1", "w2"],
            assemble_fn=montage_stage_pos_image_YX,
        )
        assert img.shape == (2, 512, 1024)
        assert len(hists) == 2
        assert "z-scaling" not in metadata
        for ch_meta in ch_metadata:
            assert "z-projection-method" in ch_meta
        # TODO: Make some checks on roi_tables (from monaging with actual
        # positions => different coordiantes)


def test_get_well_image_CYX_well_E07(files):
    files2d = files[(files["z"].isnull()) & (files["channel"].isin(["w1", "w2"]))]
    cyx, hists, ch_meta, metadata, roi_tables = get_well_image_CYX(
        well_files=files2d[files2d["well"] == "E07"], channels=["w1", "w2"]
    )

    assert cyx.shape == (2, 512, 1024)
    assert cyx.dtype == np.uint16
    assert len(hists) == 2
    assert hists[0].min() == 114
    assert hists[1].min() == 69
    assert ch_meta[0] == {
        "channel-name": "FITC_05",
        "display-color": "73ff00",
        "exposure-time": 15.0,
        "exposure-time-unit": "ms",
        "objective": "20X Plan Apo Lambda",
        "objective-numerical-aperture": 0.75,
        "power": 5.09804,
        "shading-correction": False,
        "wavelength": "cyan",
        "z-projection-method": "Maximum",
    }
    assert ch_meta[1] == {
        "channel-name": "FITC_05",
        "display-color": "73ff00",
        "exposure-time": 15.0,
        "exposure-time-unit": "ms",
        "objective": "20X Plan Apo Lambda",
        "objective-numerical-aperture": 0.75,
        "power": 5.09804,
        "shading-correction": False,
        "wavelength": "cyan",
        "z-projection-method": "Best Focus",
    }
    assert metadata == {
        "pixel-type": "uint16",
        "spatial-calibration-units": "um",
        "spatial-calibration-x": 1.3668,
        "spatial-calibration-y": 1.3668,
    }
    roi_columns = [
        "x_micrometer",
        "y_micrometer",
        "z_micrometer",
        "len_x_micrometer",
        "len_y_micrometer",
        "len_z_micrometer",
    ]
    assert list(roi_tables["well_ROI_table"].columns) == roi_columns
    assert len(roi_tables["well_ROI_table"]) == 1
    target_values = [0.0, 0.0, 0.0, 1399.6032, 699.8016, 1.0]
    assert (
        roi_tables["well_ROI_table"].loc["well_1"].values.flatten().tolist()
        == target_values
    )

    assert list(roi_tables["FOV_ROI_table"].columns) == roi_columns
    assert len(roi_tables["FOV_ROI_table"]) == 2
    target_values = [0.0, 699.8016, 0.0, 699.8016, 699.8016, 1.0]
    assert (
        roi_tables["FOV_ROI_table"].loc["Site 2"].values.flatten().tolist()
        == target_values
    )


def test_get_well_image_ZCYX(files):
    files3d = files[(~files["z"].isnull()) & (files["channel"].isin(["w1", "w2"]))]
    z_len = {"E08": 45.0, "E07": 45.289999999999054}
    for well in files3d["well"].unique():
        img, hists, ch_metadata, metadata, roi_tables = get_well_image_CZYX(
            files3d[files3d["well"] == well],
            channels=["w1", "w2"],
            assemble_fn=montage_grid_image_YX,
        )
        assert img.shape == (2, 10, 512, 1024)
        assert len(hists) == 2
        assert "z-scaling" in metadata

        roi_columns = [
            "x_micrometer",
            "y_micrometer",
            "z_micrometer",
            "len_x_micrometer",
            "len_y_micrometer",
            "len_z_micrometer",
        ]
        assert list(roi_tables["well_ROI_table"].columns) == roi_columns
        assert len(roi_tables["well_ROI_table"]) == 1
        target_values = [0.0, 0.0, 0.0, 1399.6032, 699.8016, z_len[well]]
        assert (
            roi_tables["well_ROI_table"].loc["well_1"].values.flatten().tolist()
            == target_values
        )

        assert list(roi_tables["FOV_ROI_table"].columns) == roi_columns
        assert len(roi_tables["FOV_ROI_table"]) == 2
        target_values = [0.0, 699.8016, 0.0, 699.8016, 699.8016, z_len[well]]
        assert (
            roi_tables["FOV_ROI_table"].loc["Site 2"].values.flatten().tolist()
            == target_values
        )


test_stage_labels = [
    ({"stage-label": "E07 : Site 1"}, "Site 1"),
    ({"stage-label": "E07 : Site 2"}, "Site 2"),
    ({"stage-labels": "E07 : Site 2"}, ""),
    ({}, ""),
]


@pytest.mark.parametrize("data,expected", test_stage_labels)
def test_stage_label_parser(data, expected):
    assert _stage_label(data) == expected
