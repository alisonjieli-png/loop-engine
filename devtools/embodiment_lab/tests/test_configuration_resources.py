"""Meaningful controls for actual resource handoff, tool execution, and scoring."""
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from embodiment_lab.configuration_matrix import configurations, input_population
from embodiment_lab.configuration_resources import (
    StudyInformation, apply_repairs, deterministic_assignment, evaluate_repairs, task_population)
from embodiment_lab.systematic_records import canonical
from embodiment_lab.systematic_runtime import ROOT
from loop_engine.core.context_artifacts import ContextArtifactManager, ContextArtifactServices
from loop_engine.core.information_access import InformationAccessError


def correct_decisions(cases):
    chosen=[]
    for case in cases:
        for choice in json.loads(case.choices_json):
            call=choice['replacement_call'];a,b=call['arguments'].values()
            if type(a) is not int or type(b) is not int:continue
            value={'difference':a-b,'sum':a+b,'product':a*b}[call['tool_name']]
            if value==case.expected_value:
                chosen.append({'case_id':case.case_id,'repair_id':choice['repair_id']});break
    return chosen


class ConfigurationResourceChecks(unittest.TestCase):
    def test_matrix_is_explicit_and_contains_every_named_harness_per_variant(self):
        configs=configurations()
        self.assertEqual(len(configs),40)
        self.assertEqual(len({(name,config.harness_id) for name,config in configs}),40)
        self.assertEqual(sum(c.context_delivery=='selected_references' for _,c in configs),4)

    def test_changed_input_changes_the_correct_repair_without_changing_the_menu(self):
        original,docs=input_population(False);changed,new_docs=input_population(True)
        self.assertEqual(original[0].choices_json,changed[0].choices_json)
        self.assertNotEqual(correct_decisions(original)[0],correct_decisions(changed)[0])
        self.assertEqual(sum(a!=b for a,b in zip(docs,new_docs)),1)

    def test_real_tool_execution_improves_all_four_failed_requests(self):
        with tempfile.TemporaryDirectory(prefix='repair-controls-') as directory:
            cases,docs=task_population();info=StudyInformation(directory,'controls')
            artifacts=ContextArtifactManager(ContextArtifactServices(info.store))
            application,owner=deterministic_assignment('Apply positive controls',
                lambda owner:apply_repairs(cases,correct_decisions(cases),artifacts,owner))
            evaluation=evaluate_repairs(cases,application)
            self.assertTrue(evaluation['all_passed'])
            self.assertEqual(application['physical_tool_calls'],4)
            self.assertTrue(all(x['before_error_code']=='arguments_invalid' for x in application['observations']))

    def test_valid_but_wrong_values_do_not_pass_independent_evaluation(self):
        with tempfile.TemporaryDirectory(prefix='repair-negative-') as directory:
            cases,docs=task_population();info=StudyInformation(directory,'controls')
            artifacts=ContextArtifactManager(ContextArtifactServices(info.store))
            choices=correct_decisions(cases)
            correct=choices[0]['repair_id']
            wrong=next(x['repair_id'] for x in json.loads(cases[0].choices_json)
                       if x['repair_id']!=correct and type(x['replacement_call']['arguments']['right']) is int)
            choices[0]={'case_id':cases[0].case_id,'repair_id':wrong}
            application,owner=deterministic_assignment('Apply negative control',
                lambda owner:apply_repairs(cases,choices,artifacts,owner))
            result=evaluate_repairs(cases,application)
            self.assertFalse(result['all_passed']);self.assertEqual(result['passed'],3)

    def test_duplicate_case_selection_is_refused_before_tool_execution(self):
        with tempfile.TemporaryDirectory(prefix='duplicate-selection-') as directory:
            cases,docs=task_population();info=StudyInformation(directory,'controls')
            artifacts=ContextArtifactManager(ContextArtifactServices(info.store))
            _,owner=deterministic_assignment('Create control owner',lambda owner:{'ready':True})
            with self.assertRaises(ValueError):apply_repairs(cases,[correct_decisions(cases)[0]]*4,artifacts,owner)

    def test_reference_scope_and_content_identity_survive_serialized_handoff(self):
        with tempfile.TemporaryDirectory(prefix='reference-controls-') as directory:
            _,docs=task_population();info=StudyInformation(directory,'source-run')
            _,owner=deterministic_assignment('Publish reference controls',lambda owner:info.publish(docs,owner))
            restored=StudyInformation.restore(json.loads(canonical(info.transfer())))
            loaded=restored.load(['stock-requirement'],owner)
            self.assertEqual(loaded[0],docs[0])
            with self.assertRaises(InformationAccessError):restored.load(['stock-requirement'],owner,grant=False)
            restored.run_id='unrelated-run'
            with self.assertRaises(InformationAccessError):restored.load(['stock-requirement'],owner)

    def test_separate_consumer_process_loads_exact_content_without_provider_credentials(self):
        with tempfile.TemporaryDirectory(prefix='reference-process-') as directory:
            _,docs=task_population();info=StudyInformation(directory,'source-run')
            _,owner=deterministic_assignment('Publish process control',lambda owner:info.publish(docs,owner))
            packet={'handoff':info.transfer(),'resource_ids':['balance-requirement'],
                    'history_directory':str(Path(directory)/'consumer-history')}
            result=subprocess.run([sys.executable,'-m','embodiment_lab.configuration_matrix','--resolve-references'],
                input=canonical(packet),text=True,capture_output=True,check=True,timeout=30,cwd=ROOT,
                env={'PATH':'/usr/bin:/bin','PYTHONPATH':str(ROOT/'src')+':'+str(ROOT/'devtools'),
                     'PYTHONDONTWRITEBYTECODE':'1','LANG':'C.UTF-8','TMPDIR':'/var/tmp'})
            value=json.loads(result.stdout)
            self.assertEqual(value['material'][0]['resource_id'],'balance-requirement')
            self.assertNotEqual(value['process_id'],os.getpid())
            self.assertFalse(value['provider_credential_present'])
            self.assertTrue(value['history']['verification']['intact'])


if __name__=='__main__':unittest.main()
