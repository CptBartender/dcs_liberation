import logging
import random
from enum import Enum
from typing import Dict, List

from game.data.groundunitclass import GroundUnitClass
from game.dcs.groundunittype import GroundUnitType
from game.theater import ControlPoint
from gen.ground_forces.combat_stance import CombatStance

MAX_COMBAT_GROUP_PER_CP = 10


class CombatGroupRole(Enum):
    TANK = 1
    APC = 2
    IFV = 3
    ARTILLERY = 4
    SHORAD = 5
    LOGI = 6
    INFANTRY = 7
    ATGM = 8
    RECON = 9


DISTANCE_FROM_FRONTLINE = {
    CombatGroupRole.TANK: (2200, 3200),
    CombatGroupRole.APC: (2700, 3700),
    CombatGroupRole.IFV: (2700, 3700),
    CombatGroupRole.ARTILLERY: (16000, 18000),
    CombatGroupRole.SHORAD: (5000, 8000),
    CombatGroupRole.LOGI: (18000, 20000),
    CombatGroupRole.INFANTRY: (2800, 3300),
    CombatGroupRole.ATGM: (5200, 6200),
    CombatGroupRole.RECON: (2000, 3000),
}

GROUP_SIZES_BY_COMBAT_STANCE = {
    CombatStance.DEFENSIVE: [2, 4, 6],
    CombatStance.AGGRESSIVE: [2, 4, 6],
    CombatStance.RETREAT: [2, 4, 6, 8],
    CombatStance.BREAKTHROUGH: [4, 6, 6, 8],
    CombatStance.ELIMINATION: [2, 4, 4, 4, 6],
    CombatStance.AMBUSH: [1, 1, 2, 2, 2, 2, 4],
}


class CombatGroup:
    def __init__(
        self, role: CombatGroupRole, unit_type: GroundUnitType, size: int
    ) -> None:
        self.unit_type = unit_type
        self.size = size
        self.role = role
        self.assigned_enemy_cp = None
        self.start_position = None

    def __str__(self):
        s = f"ROLE : {self.role}\n"
        if self.size:
            s += f"UNITS {self.unit_type} * {self.size}"
        return s


class GroundPlanner:
    def __init__(self, cp: ControlPoint, game):
        self.cp = cp
        self.game = game
        self.connected_enemy_cp = [
            cp for cp in self.cp.connected_points if cp.captured != self.cp.captured
        ]
        self.tank_groups: List[CombatGroup] = []
        self.apc_group: List[CombatGroup] = []
        self.ifv_group: List[CombatGroup] = []
        self.art_group: List[CombatGroup] = []
        self.atgm_group: List[CombatGroup] = []
        self.logi_groups: List[CombatGroup] = []
        self.shorad_groups: List[CombatGroup] = []
        self.recon_groups: List[CombatGroup] = []

        self.units_per_cp: Dict[int, List[CombatGroup]] = {}
        for cp in self.connected_enemy_cp:
            self.units_per_cp[cp.id] = []
        self.reserve: List[CombatGroup] = []

    def plan_groundwar(self):

        ground_unit_limit = self.cp.frontline_unit_count_limit

        remaining_available_frontline_units = ground_unit_limit

        if hasattr(self.cp, "stance"):
            group_size_choice = GROUP_SIZES_BY_COMBAT_STANCE[self.cp.stance]
        else:
            self.cp.stance = CombatStance.DEFENSIVE
            group_size_choice = GROUP_SIZES_BY_COMBAT_STANCE[CombatStance.DEFENSIVE]

        # Create combat groups and assign them randomly to each enemy CP
        for unit_type in self.cp.base.armor:
            unit_class = unit_type.unit_class
            if unit_class is GroundUnitClass.Tank:
                collection = self.tank_groups
                role = CombatGroupRole.TANK
            elif unit_class is GroundUnitClass.Apc:
                collection = self.apc_group
                role = CombatGroupRole.APC
            elif unit_class is GroundUnitClass.Artillery:
                collection = self.art_group
                role = CombatGroupRole.ARTILLERY
            elif unit_class is GroundUnitClass.Ifv:
                collection = self.ifv_group
                role = CombatGroupRole.IFV
            elif unit_class is GroundUnitClass.Logistics:
                collection = self.logi_groups
                role = CombatGroupRole.LOGI
            elif unit_class is GroundUnitClass.Atgm:
                collection = self.atgm_group
                role = CombatGroupRole.ATGM
            elif unit_class is GroundUnitClass.Shorads:
                collection = self.shorad_groups
                role = CombatGroupRole.SHORAD
            elif unit_class is GroundUnitClass.Recon:
                collection = self.recon_groups
                role = CombatGroupRole.RECON
            else:
                logging.warning(
                    f"Unused front line vehicle at base {unit_type}: unknown unit class"
                )
                continue

            available = self.cp.base.armor[unit_type]

            if available > remaining_available_frontline_units:
                available = remaining_available_frontline_units

            remaining_available_frontline_units -= available

            while available > 0:

                if role == CombatGroupRole.SHORAD:
                    count = 1
                else:
                    count = random.choice(group_size_choice)
                    if count > available:
                        if available >= 2:
                            count = 2
                        else:
                            count = 1
                available -= count

                group = CombatGroup(role, unit_type, count)
                if len(self.connected_enemy_cp) > 0:
                    enemy_cp = random.choice(self.connected_enemy_cp).id
                    self.units_per_cp[enemy_cp].append(group)
                    group.assigned_enemy_cp = enemy_cp
                else:
                    self.reserve.append(group)
                    group.assigned_enemy_cp = "__reserve__"
                collection.append(group)

            if remaining_available_frontline_units == 0:
                break

        print("------------------")
        print("Ground Planner : ")
        print(self.cp.name)
        print("------------------")
        for unit_type in self.units_per_cp.keys():
            print("For : #" + str(unit_type))
            for group in self.units_per_cp[unit_type]:
                print(str(group))
