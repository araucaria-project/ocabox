import logging
from typing import List, Any, Callable
import asyncio
from ob.planrunner.observation_plan import ObservationPlan
from ob.planrunner.coded_error import CantOverideNightPlanError
from pyaraucaria.obs_plan.obs_plan_parser import ObsPlanParser


log = logging.getLogger(__name__.rsplit('.')[-1])


class PlanRunner:

    def __init__(self, client_name: str, observ_plan_id: str, telescope: 'Telescope'):
        self.client_name = client_name
        self.observ_plan_id = observ_plan_id
        self.telescope = telescope
        self.parsed_plan: List[Any] or None = None
        self.plan_string: str or None = None
        self.info_callback = {}
        self.observation_plan = self._get_observation_plan()
        self._set_defaut_info_callback()
        self.tsk: asyncio.Task or None = None
        super().__init__()

    def _get_observation_plan(self):
        return ObservationPlan(client_name=self.client_name,
                               observ_plan_id=self.observ_plan_id,
                               telescope=self.telescope
                               )

    def _set_defaut_info_callback(self):
        self.add_info_callback('stream_1', log.info)
        self.add_info_callback('stream_2', log.info)
        self.add_info_callback('stream_3', log.info)
        self.add_info_callback('stream_4', log.info)
        self.add_info_callback('stream_5', log.info)
        self.add_info_callback('stream_6', log.info)

    def load_nightplan_string(self, nightplan_id: str, string: str, overwrite: bool = False) -> None:
        """

        :param nightplan_id: Night plan id (default: julian night date)
        :param string:
        :param overwrite: if false night plan not be written
        :return:
        """
        # TODO keep nightplans in settings, only load plans for night, else delete from memory.
        self.plan_string = string
        self._parse_plan()
        if self.parsed_plan is not None:
            try:
                self.observation_plan.write_nightplan(nightplan_id, self.parsed_plan, overwrite=overwrite)
                self.info_callback['stream_1'](f'Nightplan {nightplan_id} written')
            except CantOverideNightPlanError:
                log.error(f'Cannot overwrite nightplan {nightplan_id}, please select overwrite=True')
                self.info_callback['stream_1'](f'Cannot overwrite nightplan {nightplan_id}, please select overwrite=True')
        else:
            log.error(f'Plan is parsed wrong. Check the syntax.')
            self.info_callback['stream_1'](f'Plan is parsed wrong. Check the syntax. No plan is written')

    def delete_nightplan(self, nightplan_id: str) -> None:
        """
        Delete loaded night plan from observation plan.
        :param nightplan_id: Night plan id (default: julian night date)
        :return: None
        """
        self.observation_plan.delete_nightplan(nightplan_id)

    def add_info_callback(self, name: str, info_callback: Callable) -> None:
        """
        Method set callback for plan runner information stream.
        :param name:
            stream_1 - current executing full name (all objects)
            stream_2 - subcommands written
            stream_3 - commands written
            stream_4 - sequences written
            stream_5 - finished id
            stream_6 -
        :param info_callback: set callback method
        :return: None
        """
        self.info_callback[name] = info_callback
        self.observation_plan.info_callback[name] = info_callback

    def _parse_plan(self) -> None:
        if self.plan_string:
            parser = ObsPlanParser()
            try:
                self.parsed_plan = parser.convert_from_string(self.plan_string)
                log.debug(f'Parsed: {self.parsed_plan}')
            except Exception as e:
                self.info_callback['stream_1'](f'Cannot parse plan - please check the syntax')
                log.error(f'Cannot parse plan - please check the syntax')
        else:
            log.error(f'No plan to parse.')


    def run_nightplan(self, nightplan_id: str, step_id: str or None = None) -> None:
        """
        Method run night plan.
        :param nightplan_id:  Night plan id (default: julian night date)
        :param step_id: optional, run from specified step, example: '00' or '00_01_02' or '00_02'
        :return: None
        """
        self.stop_nightplan()
        if self.observation_plan.get_nightplan(nightplan_id):
            if self.tsk is None:
                self.tsk = asyncio.create_task(self.observation_plan.arun_night(nightplan_id, step_id=step_id))

    def stop_nightplan(self) -> None:
        """
        Method stops night plan.
        :return: None
        """
        if self.tsk:
            self.tsk.cancel()
            self.info_callback['stream_1'](f'Nightplan stopped')
            self.tsk = None
        self.tsk = None




input_1 = """
            BEGINSEQUENCE ak=6
               OBJECT FF_Aql 18:58:14.75 17:21:39.29 seq=5/I/60,5/V/70
               BEGINSEQUENCE focus=+30
                   OBJECT V496_Aql 19:08:20.77 -07:26:15.89 seq=1/V/20
                   OBJECT V496_Aql 19:08:20.77 -07:26:15.89 seq=1/V/20
               ENDSEQUENCE
            ENDSEQUENCE
           """
input_2 = """
            BEGINSEQUENCE x y z execute_at_time=16:00
                ZERO seq=15/I/0
                DARK seq=10/V/300,10/I/200
                BEGINSEQUENCE abc=13
                    DOMEFLAT seq=7/V/3,7/I/3
                    BEGINSEQUENCE
                        DOMEFLAT seq=10/str_u/100 domeflat_lamp=0.7
                    ENDSEQUENCE
                ENDSEQUENCE
                OBJECT FF_Aql 18:58:14.75 17:21:39.29 seq=2/I/4,2/V/2
            ENDSEQUENCE

            BEGINSEQUENCE execute_periodically=02:00 priority=+10
                FOCUS NG31 12:12:12 20:20:20
            ENDSEQUENCE
            """

input_3 = """
            WAIT sunset=-12
            
            FOCUS NG31 12:12:12 20:20:20
            
            OBJECT HD193901 18.8 17.0 seq=7/V/20,7/I/20
            OBJECT FF_Aql 18:58:14.75 +17:21:39.29 seq=7/V/20,7/I/20
            OBJECT V496_Aql 19:08:20.77 -07:26:15.89 seq=7/V/20,7/I/20
            OBJECT Y_Oph 17:52:38.70 -06:08:36.87 seq=7/V/20,7/I/20
            OBJECT S_Sge 19:56:01.26 +16:38:05.27 seq=7/V/20,7/I/20
            OBJECT V2022_Sgr 18:40:39.00 -25:22:50.00 seq=7/V/20,7/I/20
            OBJECT V741_Sgr 18:20:46.04 -29:48:46.40 seq=7/V/20,7/I/20
            OBJECT FM_Del 20:33:44.26 +16:16:17.59 seq=7/V/20,7/I/20
            OBJECT AV_Peg 21:52:02.795 +22:34:29.376 seq=7/V/20,7/I/20
            OBJECT RS_Gru 21:43:04.22007 -48:11:22.1783 seq=7/V/20,7/I/20
            OBJECT CS_Eri 02:37:05.758 -42:57:48.036 seq=7/V/20,7/I/20
            OBJECT GP_And 00:55:18.14771 +23:09:49.3634 seq=7/V/20,7/I/20
            OBJECT BB_Eri 04:53:37.518 -19:26:01.065 no 900 1  nv_overhead=300  Type=RRLYR  mV=11.74
            OBJECT RX_Eri 04:49:44.292 -15:44:28.243 seq=7/V/20,7/I/20
            OBJECT U_Lep 04:56:17.985 -21:13:02.024 seq=7/V/20,7/I/20
            OBJECT V764_Mon 07:37:43.200 -07:43:37.985 seq=7/V/20,7/I/20
            OBJECT V753_Cen 11:51:15.309 -55:48:15.811 seq=7/V/20,7/I/20
            OBJECT WY_Ant 10:16:04.946 -29:43:42.417 seq=7/V/20,7/I/20
            OBJECT WZ_Hya 10:13:24.127 -13:08:17.360 seq=7/V/20,7/I/20
            OBJECT AD_CMi 07:52:47.18247 +01:35:50.4974 seq=7/V/20,7/I/20
            OBJECT VZ_Cnc 08:40:52.12545 +09:49:27.1487 seq=7/V/20,7/I/20
            OBJECT V474_Mon 05:59:01.08067 -09:22:56.0055 seq=7/V/20,7/I/20
            OBJECT VX_Hya 09:45:46.84963 -12:00:14.3583 seq=7/V/20,7/I/20
            OBJECT AI_Vel 08:14:05.14681 -44:34:32.8476 seq=7/V/20,7/I/20
            """


#pr = PlanRunner('DefaultClient', 'Observ_plan_1', obs)
#pr.load_night_plan_string('112232322', input_3)
#pr.load_night_plan_string('112232333', input_2)
#pr.load_night_plan_string('112232322', input, overwrite=True)

#pr.run_night('112232322')
