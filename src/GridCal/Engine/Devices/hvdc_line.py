# This file is part of GridCal.
#
# GridCal is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# GridCal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GridCal.  If not, see <http://www.gnu.org/licenses/>.


import pandas as pd
import numpy as np
from matplotlib import pyplot as plt

from GridCal.Engine.basic_structures import Logger
from GridCal.Engine.Devices.bus import Bus
from GridCal.Engine.Devices.types import BranchType
from GridCal.Engine.Devices.underground_line import UndergroundLineType

from GridCal.Engine.Devices.editable_device import EditableDevice, DeviceType, GCProp
from GridCal.Engine.Devices.tower import Tower


class HvdcLine(EditableDevice):
    """
    The **Line** class represents the connections between nodes (i.e.
    :ref:`buses<bus>`) in **GridCal**. A branch is an element (cable, line, capacitor,
    transformer, etc.) with an electrical impedance. The basic **Branch** class
    includes basic electrical attributes for most passive elements, but other device
    types may be passed to the **Branch** constructor to configure it as a specific
    type.

    For example, a transformer may be created with the following code:

    .. code:: ipython3

        from GridCal.Engine.Core.multi_circuit import MultiCircuit
        from GridCal.Engine.Devices import *
        from GridCal.Engine.Devices.types import *

        # Create grid
        grid = MultiCircuit()

        # Create buses
        POI = Bus(name="POI",
                  vnom=100, #kV
                  is_slack=True)
        grid.add_bus(POI)

        B_C3 = Bus(name="B_C3",
                   vnom=10) #kV
        grid.add_bus(B_C3)

        # Create transformer types
        SS = TransformerType(name="SS",
                             hv_nominal_voltage=100, # kV
                             lv_nominal_voltage=10, # kV
                             nominal_power=100, # MVA
                             copper_losses=10000, # kW
                             iron_losses=125, # kW
                             no_load_current=0.5, # %
                             short_circuit_voltage=8) # %
        grid.add_transformer_type(SS)

        # Create transformer
        X_C3 = Branch(bus_from=POI,
                      bus_to=B_C3,
                      name="X_C3",
                      branch_type=BranchType.Transformer,
                      template=SS,
                      )

        # Add transformer to grid
        grid.add_branch(X_C3)

    Refer to the :class:`GridCal.Engine.Devices.branch.TapChanger` class for an example
    using a voltage regulator.

    Arguments:

        **bus_from** (:ref:`Bus`): "From" :ref:`bus<Bus>` object

        **bus_to** (:ref:`Bus`): "To" :ref:`bus<Bus>` object

        **name** (str, "Branch"): Name of the branch

        **r** (float, 1e-20): Branch resistance in per unit

        **x** (float, 1e-20): Branch reactance in per unit

        **g** (float, 1e-20): Branch shunt conductance in per unit

        **b** (float, 1e-20): Branch shunt susceptance in per unit

        **rate** (float, 1.0): Branch rate in MVA

        **tap** (float, 1.0): Branch tap module

        **shift_angle** (int, 0): Tap shift angle in radians

        **active** (bool, True): Is the branch active?

        **tolerance** (float, 0): Tolerance specified for the branch impedance in %

        **mttf** (float, 0.0): Mean time to failure in hours

        **mttr** (float, 0.0): Mean time to recovery in hours

        **r_fault** (float, 0.0): Mid-line fault resistance in per unit (SC only)

        **x_fault** (float, 0.0): Mid-line fault reactance in per unit (SC only)

        **fault_pos** (float, 0.0): Mid-line fault position in per unit (0.0 = `bus_from`, 0.5 = middle, 1.0 = `bus_to`)

        **branch_type** (BranchType, BranchType.Line): Device type enumeration (ex.: :class:`GridCal.Engine.Devices.transformer.TransformerType`)

        **length** (float, 0.0): Length of the branch in km

        **vset** (float, 1.0): Voltage set-point of the voltage controlled bus in per unit

        **temp_base** (float, 20.0): Base temperature at which `r` is measured in °C

        **temp_oper** (float, 20.0): Operating temperature in °C

        **alpha** (float, 0.0033): Thermal constant of the material in °C

        **bus_to_regulated** (bool, False): Is the `bus_to` voltage regulated by this branch?

        **template** (BranchTemplate, BranchTemplate()): Basic branch template
    """

    def __init__(self, bus_from: Bus = None, bus_to: Bus = None, name='Line', r=1e-20, psch=0.0,
                 rate=1.0, active=True, tolerance=0, cost=0.0,
                 mttf=0, mttr=0, r_fault=0.0, x_fault=0.0, fault_pos=0.5,
                 branch_type: BranchType = BranchType.Line, length=1,
                 temp_base=20, temp_oper=20, alpha=0.00330):

        EditableDevice.__init__(self,
                                name=name,
                                active=active,
                                device_type=DeviceType.HVDCLineDevice,
                                editable_headers={'name': GCProp('', str, 'Name of the branch.'),
                                                  'bus_from': GCProp('', DeviceType.BusDevice,
                                                                     'Name of the bus at the "from" side of the branch.'),
                                                  'bus_to': GCProp('', DeviceType.BusDevice,
                                                                   'Name of the bus at the "to" side of the branch.'),
                                                  'active': GCProp('', bool, 'Is the branch active?'),
                                                  'rate': GCProp('MVA', float, 'Thermal rating power of the branch.'),
                                                  'mttf': GCProp('h', float, 'Mean time to failure, '
                                                                 'used in reliability studies.'),
                                                  'mttr': GCProp('h', float, 'Mean time to recovery, '
                                                                 'used in reliability studies.'),
                                                  'R': GCProp('p.u.', float, 'Total resistance.'),
                                                  'Psch': GCProp('MW', float, 'Scheduled power.'),
                                                  'tolerance': GCProp('%', float,
                                                                      'Tolerance expected for the impedance values\n'
                                                                      '7% is expected for transformers\n'
                                                                      '0% for lines.'),
                                                  'length': GCProp('km', float, 'Length of the branch '
                                                                   '(not used for calculation)'),
                                                  'vset': GCProp('p.u.', float, 'Objective voltage at the "to" side of '
                                                                 'the bus when regulating the tap.'),
                                                  'temp_base': GCProp('ºC', float, 'Base temperature at which R was '
                                                                      'measured.'),
                                                  'temp_oper': GCProp('ºC', float, 'Operation temperature to modify R.'),
                                                  'alpha': GCProp('1/ºC', float, 'Thermal coefficient to modify R,\n'
                                                                  'around a reference temperature\n'
                                                                  'using a linear approximation.\n'
                                                                  'For example:\n'
                                                                  'Copper @ 20ºC: 0.004041,\n'
                                                                  'Copper @ 75ºC: 0.00323,\n'
                                                                  'Annealed copper @ 20ºC: 0.00393,\n'
                                                                  'Aluminum @ 20ºC: 0.004308,\n'
                                                                  'Aluminum @ 75ºC: 0.00330'),
                                                  'Cost': GCProp('e/MWh', float,
                                                                 'Cost of overloads. Used in OPF.'),
                                                  'r_fault': GCProp('p.u.', float, 'Resistance of the mid-line fault.\n'
                                                                    'Used in short circuit studies.'),
                                                  'x_fault': GCProp('p.u.', float, 'Reactance of the mid-line fault.\n'
                                                                    'Used in short circuit studies.'),
                                                  'fault_pos': GCProp('p.u.', float,
                                                                      'Per-unit positioning of the fault:\n'
                                                                      '0 would be at the "from" side,\n'
                                                                      '1 would be at the "to" side,\n'
                                                                      'therefore 0.5 is at the middle.'),
                                                  'branch_type': GCProp('', BranchType, ''),
                                                  },
                                non_editable_attributes=['bus_from', 'bus_to', 'template'],
                                properties_with_profile={'active': 'active_prof',
                                                         'Psch': 'Psch_prof',
                                                         'rate': 'rate_prof',
                                                         'temp_oper': 'temp_oper_prof',
                                                         'Cost': 'Cost_prof'})

        # connectivity
        self.bus_from = bus_from
        self.bus_to = bus_to

        # List of measurements
        self.measurements = list()

        # line length in km
        self.length = length

        # branch impedance tolerance
        self.tolerance = tolerance

        # short circuit impedance
        self.r_fault = r_fault
        self.x_fault = x_fault
        self.fault_pos = fault_pos

        # total impedance and admittance in p.u.
        self.R = r

        self.Psch = psch

        self.mttf = mttf

        self.mttr = mttr

        self.Cost = cost

        self.Cost_prof = None

        self.Psch_prof = None

        self.active_prof = None

        # Conductor base and operating temperatures in ºC
        self.temp_base = temp_base
        self.temp_oper = temp_oper

        self.temp_oper_prof = None

        # Conductor thermal constant (1/ºC)
        self.alpha = alpha

        # branch rating in MVA
        self.rate = rate

        self.rate_prof = None

        # branch type: Line, Transformer, etc...
        self.branch_type = branch_type

    @property
    def R_corrected(self):
        """
        Returns a temperature corrected resistance based on a formula provided by:
        NFPA 70-2005, National Electrical Code, Table 8, footnote #2; and
        https://en.wikipedia.org/wiki/Electrical_resistivity_and_conductivity#Linear_approximation
        (version of 2019-01-03 at 15:20 EST).
        """
        return self.R * (1 + self.alpha * (self.temp_oper - self.temp_base))

    def copy(self, bus_dict=None):
        """
        Returns a copy of the branch
        @return: A new  with the same content as this
        """

        if bus_dict is None:
            f = self.bus_from
            t = self.bus_to
        else:
            f = bus_dict[self.bus_from]
            t = bus_dict[self.bus_to]

        b = HvdcLine(bus_from=f,
                     bus_to=t,
                     name=self.name,
                     r=self.R,
                     psch=self.Psch,
                     rate=self.rate,
                     active=self.active,
                     mttf=self.mttf,
                     mttr=self.mttr,
                     temp_base=self.temp_base,
                     temp_oper=self.temp_oper,
                     alpha=self.alpha,
                     branch_type=self.branch_type)

        b.measurements = self.measurements

        b.active_prof = self.active_prof.copy()

        return b

    def apply_template(self, obj: Tower, Sbase, logger=Logger()):
        """
        Apply a branch template to this object

        Arguments:

            **obj**: TransformerType or Tower object

            **Sbase** (float): Nominal power in MVA

            **logger** (list, []): Log list

        """
        from warnings import warn
        warn('apply_template not implemented in HVDC lines')

    def get_save_data(self):
        """
        Return the data that matches the edit_headers
        :return:
        """
        data = list()
        for name, properties in self.editable_headers.items():
            obj = getattr(self, name)

            if properties.tpe == BranchType:
                obj = self.branch_type.value

            elif properties.tpe not in [str, float, int, bool]:
                obj = str(obj)

            data.append(obj)
        return data

    def get_json_dict(self, id, bus_dict):
        """
        Get json dictionary
        :param id: ID: Id for this object
        :param bus_dict: Dictionary of buses [object] -> ID
        :return:
        """

        d = {'id': id,
             'type': 'branch',
             'phases': 'ps',
             'name': self.name,
             'from': bus_dict[self.bus_from],
             'to': bus_dict[self.bus_to],
             'active': self.active,
             'rate': self.rate,
             'r': self.R,
             'length': self.length,
             'temp_base': self.temp_base,
             'temp_oper': self.temp_oper,
             'alpha': self.alpha,
             'branch_type': str(self.branch_type),
             'active_profile': [],
             'rate_prof': []}

        if self.active_prof is not None:
            d['active_profile'] = self.active_prof.tolist()
            d['rate_prof'] = self.rate_prof.tolist()

        return d

    def plot_profiles(self, time_series=None, my_index=0, show_fig=True):
        """
        Plot the time series results of this object
        :param time_series: TimeSeries Instance
        :param my_index: index of this object in the simulation
        :param show_fig: Show the figure?
        """

        if time_series is not None:
            fig = plt.figure(figsize=(12, 8))

            ax_1 = fig.add_subplot(211)
            ax_2 = fig.add_subplot(212)

            x = time_series.results.time

            # loading
            y = time_series.results.loading * 100.0
            df = pd.DataFrame(data=y[:, my_index], index=x, columns=[self.name])
            ax_1.set_title('Loading', fontsize=14)
            ax_1.set_ylabel('Loading [%]', fontsize=11)
            df.plot(ax=ax_1)

            # losses
            y = time_series.results.losses
            df = pd.DataFrame(data=y[:, my_index], index=x, columns=[self.name])
            ax_2.set_title('Losses', fontsize=14)
            ax_2.set_ylabel('Losses [MVA]', fontsize=11)
            df.plot(ax=ax_2)

            plt.legend()
            fig.suptitle(self.name, fontsize=20)

        if show_fig:
            plt.show()

    def get_coordinates(self):
        """
        Get the branch defining coordinates
        """
        return [self.bus_from.get_coordinates(), self.bus_to.get_coordinates()]
