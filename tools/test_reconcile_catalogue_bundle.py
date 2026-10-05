"""Exact baseline preservation; synthetic packages, no provider or production calls."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

import reconcile_catalogue_bundle as reconcile
from loop_engine.core.harness_intelligence import HarnessIntelligenceDraft, item_from_body
from loop_engine.core.service_runtime.catalogue_bundle import write_bundle
from loop_engine.core.service_runtime.catalogue_packages import CataloguePackage, CataloguePackageFile, sha256_hex
from loop_engine.core.service_runtime.catalogue_schema import EMPTY_SCHEMA


def line(identity, body, *, attributes=None):
    item = item_from_body(HarnessIntelligenceDraft(identity, 'skill', 'Synthetic reusable method',
        'harness_local', 'fixture:' + identity, 'MIT'), body)
    package = CataloguePackage((CataloguePackageFile('SKILL.md', sha256_hex(body.encode()),
        len(body.encode()), 'text/markdown', 'skill_definition'),), 'file')
    return {'record_type': 'catalogue_bundle_item/v2', 'reference': item.reference(),
            'package': package.to_dict(), 'approval': {'approval_ref': 'fixture-review#' + identity,
            'approved_digest': item.digest, 'tier': 'community'}, 'attributes': attributes or {}}


def bundle(folder, rows, bodies, *, schema=EMPTY_SCHEMA):
    write_bundle(folder, schema=schema, lines=rows, payloads=[value.encode() for value in bodies])
    return reconcile.load_bundle(folder, ('MIT',))


def request(base, *, additions=(), replacements=(), withdrawals=()):
    return reconcile.Changes.from_dict({'record_type': reconcile.REQUEST_VERSION,
        'base_release': 'a' * 64, 'base_bundle_digest': base.digest,
        'additions': list(additions), 'replacements': list(replacements), 'withdrawals': list(withdrawals)})


def observation(base):
    return {'record_type': 'service_catalogue_view/v1', 'release_id': 'a' * 64,
        'content_digest': reconcile.bundle_content(base), 'schema_digest': base.schema.digest,
        'items': len(base.items), 'withdrawn_left_out': 0}


class PreservationChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = bundle(self.root / 'base', [line('old', 'retained bytes')], ['retained bytes'])
        self.add = bundle(self.root / 'add', [line('new', 'new bytes')], ['new bytes'])
        self.changes = request(self.base, additions=('new',))

    def test_addition_retains_exact_old_row_and_version(self):
        result = reconcile.compose(self.base, (self.add,), self.changes)
        self.assertEqual(result.rows['old'], reconcile.bundle_rows(self.base)['old'])
        self.assertEqual(result.versions['old'], self.base.items[0].version)
        self.assertEqual(set(result.rows), {'old', 'new'})

    def test_missing_live_row_is_not_an_implicit_withdrawal(self):
        with self.assertRaisesRegex(ValueError, 'preservation'):
            reconcile.validate_result(self.base, self.add, self.changes)

    def test_batch_only_retagging_cannot_replace_an_old_version(self):
        # Mutant of the old daily builder: only an internal attribute changes.
        from loop_engine.core.service_runtime.catalogue_schema import CatalogueAttributeSchema, CatalogueAttribute
        schema = CatalogueAttributeSchema((CatalogueAttribute('batch', 'keyword', visibility='internal'),))
        old = bundle(self.root / 'tag-base', [line('old', 'same', attributes={'batch':'before'})], ['same'], schema=schema)
        new = bundle(self.root / 'tag-new', [line('old', 'same', attributes={'batch':'after'})], ['same'], schema=schema)
        changes = request(old, replacements=({'identity':'old', 'expected_version':old.items[0].version},))
        with self.assertRaisesRegex(ValueError, 'batch-only'):
            reconcile.compose(old, (new,), changes)

    def test_replacement_requires_exact_old_version(self):
        replacement = bundle(self.root / 'replacement', [line('old', 'new method')], ['new method'])
        wrong = request(self.base, replacements=({'identity':'old','expected_version':'0'*64},))
        with self.assertRaisesRegex(ValueError, 'expected version'):
            reconcile.compose(self.base, (replacement,), wrong)
        right = request(self.base, replacements=({'identity':'old','expected_version':self.base.items[0].version},))
        self.assertEqual(reconcile.compose(self.base, (replacement,), right).versions['old'], replacement.items[0].version)

    def test_withdrawal_requires_exact_old_version_and_note(self):
        changes = request(self.base, additions=('new',), withdrawals=({'identity':'old',
            'expected_version':self.base.items[0].version,'note':'Explicit synthetic withdrawal'},))
        result = reconcile.compose(self.base, (self.add,), changes)
        self.assertEqual(set(result.rows), {'new'})
        self.assertEqual(result.withdrawals, ({'identity':'old','note':'Explicit synthetic withdrawal'},))
        with self.assertRaises(ValueError):
            request(self.base, withdrawals=({'identity':'old','expected_version':'a'*64,'note':''},))

    def test_later_addition_does_not_replay_historical_withdrawal_notes(self):
        changes=request(self.base,additions=('new',),withdrawals=({'identity':'old',
            'expected_version':self.base.items[0].version,'note':'Explicit withdrawal'},))
        first=self.root/'withdrawn-base'
        reconcile.write_reconciled(self.base,(self.add,),changes,first,observation(self.base))
        held=reconcile.load_bundle(first,('MIT',))
        update=bundle(self.root/'third',[line('third','third method')],['third method'])
        output=self.root/'after-withdrawal'
        reconcile.write_reconciled(held,(update,),request(held,additions=('third',)),output,
            observation(held),extra_roots=(self.add.folder/'blobs',))
        final=reconcile.load_bundle(output,('MIT',))
        self.assertEqual(final.withdrawals,())
        self.assertNotIn('old',final.change_notes)

    def test_undeclared_addition_or_collision_refused(self):
        with self.assertRaisesRegex(ValueError, 'declarations'):
            reconcile.compose(self.base, (self.add,), request(self.base))
        with self.assertRaises(ValueError):
            reconcile.compose(self.base, (self.add, self.add), self.changes)
        with self.assertRaises(ValueError):
            request(self.base, additions=('new','new'))

    def test_unknown_request_version_or_field_refused(self):
        for value in ({**self.changes.to_dict(), 'record_type':'catalogue_reconciliation_request/v99'},
                      {**self.changes.to_dict(), 'allow_drop':True}):
            with self.assertRaises(ValueError):reconcile.Changes.from_dict(value)

    def test_typed_constructor_does_not_bypass_request_validation(self):
        with self.assertRaises(ValueError):
            reconcile.Changes('a'*64,self.base.digest,('new','new'),(),())

    def test_subset_schema_is_allowed_but_unknown_live_attributes_are_not(self):
        from loop_engine.core.service_runtime.catalogue_schema import CatalogueAttributeSchema,CatalogueAttribute
        schema=CatalogueAttributeSchema((CatalogueAttribute('batch','keyword',visibility='internal'),))
        base=bundle(self.root/'schema-base',[line('old','held',attributes={'batch':'before'})],['held'],schema=schema)
        self.assertEqual(set(reconcile.compose(base,(self.add,),request(base,additions=('new',))).rows),{'old','new'})
        other=bundle(self.root/'schema-other',[line('new','new',attributes={'batch':'after'})],['new'],schema=schema)
        with self.assertRaises(ValueError):
            reconcile.compose(self.base,(other,),request(self.base,additions=('new',)))

    def test_live_release_and_content_must_both_match(self):
        reconcile.require_live_base(self.base, self.changes, observation(self.base))
        for field, value in (('release_id','b'*64),('content_digest','c'*64),('schema_digest','d'*64),('items',2)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                reconcile.require_live_base(self.base, self.changes, {**observation(self.base),field:value})

    def test_delta_output_needs_explicit_baseline_blob_roots(self):
        output = self.root / 'output'
        result = reconcile.write_reconciled(self.base, (self.add,), self.changes, output, observation(self.base))
        self.assertEqual(len(list((output/'blobs/sha256').glob('*/*'))), 1)
        after = reconcile.load_bundle(output, ('MIT',))
        with self.assertRaisesRegex(ValueError, 'missing'):
            reconcile.verify_files(after, ())
        reconcile.verify_files(after, (self.base.folder/'blobs',))
        self.assertEqual(result['bundle_digest'], after.digest)
        self.assertTrue((output/reconcile.PROOF_FILE).is_file())

    def test_missing_new_blob_refuses_before_output_creation(self):
        entry = self.add.items[0].package.files[0]
        (self.add.folder/'blobs/sha256'/entry.digest[:2]/entry.digest).unlink()
        with self.assertRaises(ValueError):
            reconcile.write_reconciled(self.base,(self.add,),self.changes,self.root/'missing',observation(self.base))
        self.assertFalse((self.root/'missing').exists())

    def test_modified_output_cannot_reuse_reconciliation_proof(self):
        output=self.root/'output'
        reconcile.write_reconciled(self.base,(self.add,),self.changes,output,observation(self.base))
        proof=json.loads((output/reconcile.PROOF_FILE).read_text())
        proof['bundle_digest']='0'*64
        with self.assertRaises(ValueError):
            reconcile.check_proof(self.base,reconcile.load_bundle(output,('MIT',)),proof)
        proof=json.loads((output/reconcile.PROOF_FILE).read_text())
        proof['unchanged_items']=True
        with self.assertRaises(ValueError):
            reconcile.check_proof(self.base,reconcile.load_bundle(output,('MIT',)),proof)

    def test_real_local_service_publishes_the_predicted_release_and_preserves_old_versions(self):
        from loop_engine.core.service_runtime.catalogue_release_checks import Fixture
        from loop_engine.core.service_runtime.catalogue_releases import publish
        case=Fixture(self.root/'service')
        first=publish(case.context,self.base)
        changes=reconcile.Changes.from_dict({**self.changes.to_dict(),'base_release':first['release_id']})
        observed=case.view().summary()
        output=self.root/'journey'
        reconcile.write_reconciled(self.base,(self.add,),changes,output,observed)
        proof=json.loads((output/reconcile.PROOF_FILE).read_text())
        result=publish(case.context,reconcile.load_bundle(output,('MIT',)),expected_release=changes.base_release)
        self.assertEqual(result['release_id'],proof['result_release'])
        self.assertEqual(result['content_digest'],proof['result_content_digest'])
        self.assertEqual(case.view().item_versions['old'],self.base.items[0].version)
        self.assertEqual(set(case.view().catalogue.items),{'old','new'})

    def replaced(self, name):
        """A real local service whose live x@v1 was withdrawn and replaced by x@v2 through this tool."""
        from loop_engine.core.service_runtime.catalogue_release_checks import Fixture
        from loop_engine.core.service_runtime.catalogue_releases import publish,withdraw
        case=Fixture(self.root/name)
        base=bundle(self.root/(name+'-base'),[line('keep','keep bytes'),line('x','v1 bytes')],['keep bytes','v1 bytes'])
        first=publish(case.context,base)
        withdraw(case.context,identity='x',note_text='Synthetic: v1 had a defect')
        old=next(item.version for item in base.items if item.identity=='x')
        fix=bundle(self.root/(name+'-fix'),[line('x','v2 bytes')],['v2 bytes'])
        changes=reconcile.Changes.from_dict({**request(base,replacements=({'identity':'x','expected_version':old},)).to_dict(),
                                             'base_release':first['release_id']})
        reconcile.write_reconciled(base,(fix,),changes,self.root/(name+'-r2'),case.view().summary())
        held=reconcile.load_bundle(self.root/(name+'-r2'),('MIT',))
        second=publish(case.context,held,expected_release=first['release_id'])
        return case,base,held,second['release_id']

    def test_a_replaced_withdrawn_version_does_not_lock_the_next_delta(self):
        # Known wrong until October 5, 2026: the live summary counted the withdrawal of x@v1, which the release no
        # longer lists, so items + withdrawn_left_out exceeded the release and every later delta was refused.
        from loop_engine.core.service_runtime.catalogue_releases import publish
        case,base,held,release=self.replaced('replaced')
        observed=case.view().summary()
        self.assertEqual((observed['items'],observed['withdrawn_left_out']),(2,0))
        third=bundle(self.root/'replaced-add',[line('third','third bytes')],['third bytes'])
        changes=reconcile.Changes.from_dict({**request(held,additions=('third',)).to_dict(),'base_release':release})
        reconcile.write_reconciled(held,(third,),changes,self.root/'replaced-r3',observed,extra_roots=(base.folder/'blobs',))
        result=publish(case.context,reconcile.load_bundle(self.root/'replaced-r3',('MIT',)),expected_release=release)
        self.assertEqual((result['state'],result['items']),('published',3))

    def test_withdrawing_every_version_leaves_out_only_the_listed_one(self):
        # `withdraw --all-versions` after one replacement names x@v1 and x@v2. Only x@v2 is listed, so every view
        # (rebuilt, refreshed in place, or built from an image) leaves one out and the release dropping x can be prepared.
        from loop_engine.core.service_runtime.catalogue_releases import publish,withdraw,withdrawal_keys
        from loop_engine.core.service_runtime.catalogue_serving import image_view,next_view,state_token
        case,base,held,release=self.replaced('every-version')
        before=case.view()
        self.assertEqual(len(withdraw(case.context,identity='x',note_text='Synthetic: every version',
                                      all_versions=True)['withdrawn_versions']),1)
        with case.context.binding.store() as store:
            keys=withdrawal_keys(case.context.binding,store)
        self.assertEqual(len(keys),2)
        views={'rebuilt':case.view(),'image':image_view(before.catalogue,before.qualification_resolver,
                                                        before.body_reader,withdrawn=keys,prepare_search=False),
               'refreshed':next_view(before,state_token(case.config),case.config,case.settings,
                                     license_policy=case.license_policy,family_policy=case.family_policy)}
        for name,view in views.items():
            with self.subTest(view=name):
                self.assertEqual((view.summary()['items'],view.summary()['withdrawn_left_out']),(1,1))
        listed=next(item.version for item in held.items if item.identity=='x')
        changes=reconcile.Changes.from_dict({**request(held,withdrawals=({'identity':'x','expected_version':listed,
                                             'note':'Synthetic: remove the withdrawn item'},)).to_dict(),'base_release':release})
        reconcile.write_reconciled(held,(),changes,self.root/'every-version-r3',views['refreshed'].summary(),
                                   extra_roots=(base.folder/'blobs',))
        result=publish(case.context,reconcile.load_bundle(self.root/'every-version-r3',('MIT',)),expected_release=release)
        self.assertEqual((result['state'],result['items']),('published',1))
        self.assertEqual((case.view().summary()['items'],case.view().summary()['withdrawn_left_out']),(1,0))

    def test_a_live_row_the_service_withdrew_is_refused_before_any_write(self):
        # Known wrong until October 5, 2026: an additions-only reconciliation kept the withdrawn x, every local gate
        # passed, and the service refused only after the upload with catalogue_release_lists_withdrawn_item.
        from loop_engine.core.service_runtime.catalogue_release_checks import Fixture
        from loop_engine.core.service_runtime.catalogue_releases import publish,withdraw
        case=Fixture(self.root/'withdrawn-service')
        base=bundle(self.root/'withdrawn-live',[line('keep','keep bytes'),line('x','x bytes')],['keep bytes','x bytes'])
        first=publish(case.context,base)
        withdraw(case.context,identity='x',note_text='Synthetic withdrawal')
        observed=case.view().summary()
        kept=reconcile.Changes.from_dict({**request(base,additions=('new',)).to_dict(),'base_release':first['release_id']})
        with self.assertRaisesRegex(ValueError,'durably withdrawn'):
            reconcile.write_reconciled(base,(self.add,),kept,self.root/'withdrawn-kept',observed)
        self.assertFalse((self.root/'withdrawn-kept').exists())
        version=next(item.version for item in base.items if item.identity=='x')
        declared=reconcile.Changes.from_dict({**request(base,additions=('new',),withdrawals=({'identity':'x',
            'expected_version':version,'note':'Synthetic: withdrawn at the service'},)).to_dict(),
            'base_release':first['release_id']})
        reconcile.write_reconciled(base,(self.add,),declared,self.root/'withdrawn-declared',observed)
        result=publish(case.context,reconcile.load_bundle(self.root/'withdrawn-declared',('MIT',)),
                       expected_release=first['release_id'])
        self.assertEqual(result['state'],'published')
        self.assertEqual(set(case.view().catalogue.items),{'keep','new'})

    def test_real_local_service_rejects_a_concurrent_base_before_activation(self):
        from loop_engine.core.service_runtime.catalogue_release_checks import Fixture
        from loop_engine.core.service_runtime.catalogue_releases import publish
        from loop_engine.core.service_runtime.records import ServiceRuntimeError
        case=Fixture(self.root/'race-service')
        first=publish(case.context,self.base)
        changes=reconcile.Changes.from_dict({**self.changes.to_dict(),'base_release':first['release_id']})
        output=self.root/'race-output'
        reconcile.write_reconciled(self.base,(self.add,),changes,output,case.view().summary())
        other=bundle(self.root/'other',[line('old','held'),line('concurrent','concurrent bytes')],['held','concurrent bytes'])
        moved=publish(case.context,other,expected_release=first['release_id'])
        with self.assertRaises(ServiceRuntimeError) as refused:
            publish(case.context,reconcile.load_bundle(output,('MIT',)),expected_release=first['release_id'])
        self.assertEqual(refused.exception.code,'catalogue_pointer_moved')
        self.assertEqual(case.view().release_id,moved['release_id'])


if __name__ == '__main__':
    unittest.main()
