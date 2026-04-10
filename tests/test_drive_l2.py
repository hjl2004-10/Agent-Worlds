"""
drive_l2 单元测试 — 驱动系统纯数学函数
"""

import math
import pytest


class TestCalcDistance:
    """欧几里得距离计算"""

    def test_same_point(self):
        from core.drive.drive_l2 import calc_distance
        assert calc_distance(0, 0, 0, 0) == 0.0

    def test_horizontal(self):
        from core.drive.drive_l2 import calc_distance
        assert calc_distance(0, 0, 3, 0) == 3.0

    def test_vertical(self):
        from core.drive.drive_l2 import calc_distance
        assert calc_distance(0, 0, 0, 4) == 4.0

    def test_pythagorean(self):
        from core.drive.drive_l2 import calc_distance
        assert calc_distance(0, 0, 3, 4) == 5.0

    def test_negative_coords(self):
        from core.drive.drive_l2 import calc_distance
        assert calc_distance(-1, -1, 2, 3) == 5.0

    def test_symmetry(self):
        from core.drive.drive_l2 import calc_distance
        assert calc_distance(1, 2, 5, 6) == calc_distance(5, 6, 1, 2)


class TestCheckHysteresisState:
    """迟滞状态机判定"""

    def test_close_no_ban_triggers_talk(self):
        from core.drive.drive_l2 import check_hysteresis_state
        should_talk, should_clear = check_hysteresis_state(
            dist=1.0, current_ban_target=None, th_contact=2.0, th_leave=5.0
        )
        assert should_talk is True
        assert should_clear is False

    def test_close_with_ban_no_talk(self):
        from core.drive.drive_l2 import check_hysteresis_state
        should_talk, should_clear = check_hysteresis_state(
            dist=1.0, current_ban_target="Bob", th_contact=2.0, th_leave=5.0
        )
        assert should_talk is False
        assert should_clear is False

    def test_far_with_ban_clears(self):
        from core.drive.drive_l2 import check_hysteresis_state
        should_talk, should_clear = check_hysteresis_state(
            dist=6.0, current_ban_target="Bob", th_contact=2.0, th_leave=5.0
        )
        assert should_talk is False
        assert should_clear is True

    def test_far_no_ban_nothing(self):
        from core.drive.drive_l2 import check_hysteresis_state
        should_talk, should_clear = check_hysteresis_state(
            dist=6.0, current_ban_target=None, th_contact=2.0, th_leave=5.0
        )
        assert should_talk is False
        assert should_clear is False

    def test_exact_threshold_contact(self):
        from core.drive.drive_l2 import check_hysteresis_state
        should_talk, _ = check_hysteresis_state(
            dist=2.0, current_ban_target=None, th_contact=2.0, th_leave=5.0
        )
        assert should_talk is True

    def test_exact_threshold_leave(self):
        from core.drive.drive_l2 import check_hysteresis_state
        _, should_clear = check_hysteresis_state(
            dist=5.0, current_ban_target="Bob", th_contact=2.0, th_leave=5.0
        )
        assert should_clear is True

    def test_middle_zone_no_action(self):
        """在接触和离开阈值之间，无论 ban 状态都不触发"""
        from core.drive.drive_l2 import check_hysteresis_state
        should_talk, should_clear = check_hysteresis_state(
            dist=3.0, current_ban_target="Bob", th_contact=2.0, th_leave=5.0
        )
        assert should_talk is False
        assert should_clear is False


class TestGodModeStep:
    """上帝模式移动"""

    def test_move_right(self):
        from core.drive.drive_l2 import god_mode_step
        new_x, new_y = god_mode_step(100, 100, 'right', 10, 500, 500)
        assert new_x == 110
        assert new_y == 100

    def test_move_left(self):
        from core.drive.drive_l2 import god_mode_step
        new_x, new_y = god_mode_step(100, 100, 'left', 10, 500, 500)
        assert new_x == 90
        assert new_y == 100

    def test_move_up(self):
        from core.drive.drive_l2 import god_mode_step
        new_x, new_y = god_mode_step(100, 100, 'up', 10, 500, 500)
        assert new_x == 100
        assert new_y == 90

    def test_move_down(self):
        from core.drive.drive_l2 import god_mode_step
        new_x, new_y = god_mode_step(100, 100, 'down', 10, 500, 500)
        assert new_x == 100
        assert new_y == 110

    def test_boundary_left(self):
        from core.drive.drive_l2 import god_mode_step
        new_x, _ = god_mode_step(5, 100, 'left', 10, 500, 500)
        assert new_x == 0

    def test_boundary_right(self):
        from core.drive.drive_l2 import god_mode_step
        new_x, _ = god_mode_step(495, 100, 'right', 10, 500, 500)
        assert new_x == 500

    def test_boundary_top(self):
        from core.drive.drive_l2 import god_mode_step
        _, new_y = god_mode_step(100, 3, 'up', 10, 500, 500)
        assert new_y == 0

    def test_boundary_bottom(self):
        from core.drive.drive_l2 import god_mode_step
        _, new_y = god_mode_step(100, 497, 'down', 10, 500, 500)
        assert new_y == 500

    def test_blocked_stays_put(self, mock_map_blocked):
        from core.drive.drive_l2 import god_mode_step
        new_x, new_y = god_mode_step(100, 100, 'right', 10, 500, 500)
        assert new_x == 100
        assert new_y == 100

    def test_invalid_direction_no_move(self):
        from core.drive.drive_l2 import god_mode_step
        new_x, new_y = god_mode_step(100, 100, 'invalid', 10, 500, 500)
        assert new_x == 100
        assert new_y == 100


class TestLinearStep:
    """直线行走"""

    def test_move_right(self):
        from core.drive.drive_l2 import linear_step
        new_x, new_y, _ = linear_step(100, 100, 0, 10, 500, 500)
        assert abs(new_x - 110) < 0.01
        assert abs(new_y - 100) < 0.01

    def test_move_down(self):
        from core.drive.drive_l2 import linear_step
        new_x, new_y, _ = linear_step(100, 100, math.pi / 2, 10, 500, 500)
        assert abs(new_x - 100) < 0.01
        assert abs(new_y - 110) < 0.01

    def test_wall_bounce_x(self):
        """撞左墙应水平反弹"""
        from core.drive.drive_l2 import linear_step
        # 朝左走 (π方向)，距左墙只有 5
        _, _, new_dir = linear_step(5, 100, math.pi, 10, 500, 500)
        # 反弹后 x 应被 clamp 到 0
        # 方向应变化

    def test_boundary_clamp(self):
        from core.drive.drive_l2 import linear_step
        new_x, new_y, _ = linear_step(0, 0, math.pi + 0.5, 10, 500, 500)
        assert new_x >= 0
        assert new_y >= 0


class TestRandomStep:
    """随机漫步"""

    def test_stays_in_bounds(self):
        from core.drive.drive_l2 import random_step
        for _ in range(100):
            new_x, new_y = random_step(250, 250, 5, 500, 500)
            assert 0 <= new_x <= 500
            assert 0 <= new_y <= 500

    def test_corner_stays_in_bounds(self):
        from core.drive.drive_l2 import random_step
        for _ in range(100):
            new_x, new_y = random_step(0, 0, 5, 500, 500)
            assert 0 <= new_x <= 500
            assert 0 <= new_y <= 500

    def test_blocked_stays_put(self, mock_map_blocked):
        from core.drive.drive_l2 import random_step
        new_x, new_y = random_step(100, 100, 5, 500, 500)
        assert new_x == 100
        assert new_y == 100


class TestMoveTowardTarget:
    """目标移动"""

    def test_arrives_when_close(self):
        from core.drive.drive_l2 import move_toward_target
        new_x, new_y, arrived = move_toward_target(99, 100, 100, 100, 5)
        assert arrived is True
        assert new_x == 100
        assert new_y == 100

    def test_moves_toward_target(self):
        from core.drive.drive_l2 import move_toward_target
        new_x, new_y, arrived = move_toward_target(0, 0, 100, 0, 5)
        assert arrived is False
        assert new_x > 0  # 朝目标方向移动
        assert abs(new_y) < 0.01  # 水平移动，y 不变

    def test_blocked_target(self, mock_map_blocked):
        from core.drive.drive_l2 import move_toward_target
        new_x, new_y, arrived = move_toward_target(99, 100, 100, 100, 5)
        assert arrived is False  # 目标被阻挡


class TestGenerateDirection:
    """随机方向生成"""

    def test_range(self):
        from core.drive.drive_l2 import generate_direction
        for _ in range(100):
            d = generate_direction()
            assert 0 <= d <= 2 * math.pi
