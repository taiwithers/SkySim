from datetime import date, time, timedelta

from astropy import units as u

from skysim.outline import Settings


def test_settings() -> None:
    input_location = "Toronto"
    field_of_view = 2 * u.deg
    altitude_angle = 40 * u.deg
    azimuth_angle = 140 * u.deg
    image_pixels = 250

    start_date = date(year=2025, month=2, day=25)
    start_time = time(hour=20, minute=30)
    snapshot_frequency = timedelta(minutes=1)
    duration = timedelta(hours=1)

    settings = Settings(
        input_location,
        field_of_view,
        altitude_angle,
        azimuth_angle,
        image_pixels,
        start_date,
        start_time,
        snapshot_frequency,
        duration,
    )

    print(settings)

    return


if __name__ == "__main__":
    test_settings()
