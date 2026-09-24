/* Listing text: the names, descriptions and addresses that publishers of other products wrote, which a public
   directory of the website quotes as data. The word rules of tools/check_service_workspace.mjs (runtime words, trial
   words, invitation words) hold Baltor's own copy to the owner's vocabulary. A listing written by someone else is not
   Baltor's copy: a server called "zephyr-7b-beta" or a description that says "invite your team" is a fact about that
   product. So each directory registers exactly which of its served files carry listing text and where, and the word
   rules read everything else.

   - A JSON file registers the keys whose values are listing text. Every string under such a key, at any depth, is
     blanked before the words are read; every other key, value and the record envelope are read as before.
   - A page registers itself as a page with listing text. Only elements marked data-listing-text are left out of the
     reading, in the served markup and in the rendered page. The directory's own browser checks require that the
     marker sits only on listing fields inside a listing row.

   Nothing is exempt by default: an unregistered path is read whole, and a JSON file that does not parse is read whole,
   so a malformed file fails the word rules instead of passing them. The known-wrong controls live in
   tools/check_service_workspace.mjs beside the rules they narrow. */
export const LISTING_TEXT_ATTRIBUTE="data-listing-text";
const registered=new Map();

/* path: the served address. fields: JSON keys whose values are listing text. page: true for a page whose markup marks its
   listing fields with data-listing-text. */
export function registerListingText(path,{fields=[],page=false}={}){
  if(typeof path!=="string"||!path.startsWith("/"))throw new Error("a listing text registration names a served address");
  if(!Array.isArray(fields)||fields.some(field=>typeof field!=="string"||!field))throw new Error("listing text fields are key names");
  if(!page&&fields.length===0)throw new Error("a registration names listing text fields or marks a page");
  registered.set(path,{fields:[...fields],page:page===true});
}

export function listingTextRegistration(path){return registered.get(path)||null;}
export function listingTextPages(){return [...registered].filter(([,entry])=>entry.page).map(([path])=>path);}

function blankUnder(value,fields,inside){
  if(typeof value==="string")return inside?"":value;
  if(Array.isArray(value))return value.map(item=>blankUnder(item,fields,inside));
  if(value&&typeof value==="object")return Object.fromEntries(Object.entries(value).map(([key,item])=>[key,blankUnder(item,fields,inside||fields.includes(key))]));
  return value;
}

/* Marked elements of served markup, removed with their contents. A marked element holds no element of its own tag. */
const markedElement=new RegExp("<([a-z][a-z0-9]*)\\b[^>]*\\s"+LISTING_TEXT_ATTRIBUTE+"(?:=\"[^\"]*\")?[^>]*>[\\s\\S]*?</\\1>","gi");

/* The text the word rules read for one served file: the file itself, with its registered listing text left out. */
export function withoutListingText(path,text){
  const entry=registered.get(path);
  if(!entry||typeof text!=="string")return text;
  if(entry.page)return text.replace(markedElement,"");
  try{return JSON.stringify(blankUnder(JSON.parse(text),entry.fields,false));}
  catch(_){return text;}
}
