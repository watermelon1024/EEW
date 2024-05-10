import math


def speed_model(depth: int, distance: float) -> tuple[float, float]:
    """
    Calculate the P and S wave travel times based on the earthquake depth and distance.

    :param depth: Depth of the earthquake in kilometers.
    :type depth: int
    :param distance: Actual distance from the hypocenter to the specific point in kilometers.
    :type distance: float
    :return: P and S wave travel times.
    :rtype: tuple[float, float]
    """
    Za = depth
    if depth <= 40:
        G0, G = 5.10298, 0.06659
    else:
        G0, G = 7.804799, 0.004573
    Zc = -1 * (G0 / G)
    Xb = distance
    Xc = (Xb**2 - 2 * (G0 / G) * Za - Za**2) / (2 * Xb)

    Theta_a = math.atan((Za - Zc) / Xc)
    if Theta_a < 0:
        Theta_a += math.pi
    Theta_a = math.pi - Theta_a

    Theta_B = math.atan((-1 * Zc) / (Xb - Xc))
    p_time = (1 / G) * math.log(math.tan(Theta_a / 2) / math.tan(Theta_B / 2))

    G0_, G_ = G0 / 1.732, G / 1.732
    Zc_ = -1 * (G0_ / G_)
    Xc_ = (Xb**2 - 2 * (G0_ / G_) * Za - Za**2) / (2 * Xb)

    Theta_A_ = math.atan((Za - Zc_) / Xc_)
    if Theta_A_ < 0:
        Theta_A_ += math.pi
    Theta_A_ = math.pi - Theta_A_

    Theta_B_ = math.atan((-1 * Zc_) / (Xb - Xc_))
    s_time = (1 / G_) * math.log(math.tan(Theta_A_ / 2) / math.tan(Theta_B_ / 2))

    if distance / p_time > 7:
        p_time = distance / 7
    if distance / s_time > 4:
        s_time = distance / 4

    return p_time, s_time
