"""Create a contact sheet and UV-layout examples from actual delivered meshes."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from mesh_core import ROOT
from render_preview import render

SELECTED=['Ground_Meadow_A','Transition_Moss_A','Paving_Broken_A','Rock_Hero_Island',
          'Tank_Arc_A','Catwalk_Deck_3m','Bridge_Deck_Broken','Lattice_Pylon',
          'Truck_Abandoned','Tarp_Covered_Stack','Log_Fallen_Bridge','Banner_Still_Here',
          'Broadleaf_A','Pine_A','Bush_B','Traveller_Static']

def font(size):
    for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','C:/Windows/Fonts/arial.ttf','/System/Library/Fonts/Supplemental/Arial.ttf']:
        if Path(p).exists():return ImageFont.truetype(p,size)
    return ImageFont.load_default(size=size)


def main():
    catalog={a['id']:a for a in json.loads((ROOT/'data/assets.json').read_text())['assets']}
    for aid in SELECTED:
        render(width=600,output='previews/assets/'+aid+'.png',asset_only=aid,shadows=True,ssao=True)
    cell_w,cell_h,pad,head=400,300,14,70
    board=Image.new('RGB',(cell_w*4,cell_h*4+head),(29,42,36));d=ImageDraw.Draw(board)
    d.text((20,17),'STILL HERE — ACTUAL MESH PREVIEWS',font=font(27),fill=(225,231,214))
    d.text((20,49),'VTK render from exported mesh data • not an image-generated result board',font=font(13),fill=(158,177,162))
    for i,aid in enumerate(SELECTED):
        x=(i%4)*cell_w;y=head+(i//4)*cell_h;im=Image.open(ROOT/'previews/assets'/f'{aid}.png').convert('RGB')
        im.thumbnail((cell_w-pad*2,244),Image.Resampling.LANCZOS)
        board.paste(im,(x+(cell_w-im.width)//2,y))
        a=catalog[aid];d.text((x+pad,y+249),aid,font=font(16),fill=(223,229,211))
        d.text((x+pad,y+272),f'{a["triangles"]:,} triangles | {a["atlas_size"]}² atlas | unique UV',font=font(12),fill=(155,176,158))
    board.save(ROOT/'previews/asset_contact_sheet.jpg',quality=93,subsampling=0)
    for aid in ['Truck_Abandoned','Ground_Meadow_A','Broadleaf_A']:
        a=catalog[aid];im=Image.open(ROOT/a['base_color']).convert('RGB');uv=json.loads((ROOT/f'data/uv/{aid}.json').read_text())
        draw=ImageDraw.Draw(im)
        for c in uv['charts']:
            x,y,w,h=c['rect_pixels'];draw.rectangle((x,y,x+w-1,y+h-1),outline=(238,239,211),width=1)
        side=min(1024,im.width);im=im.resize((side,side),Image.Resampling.LANCZOS)
        page=Image.new('RGB',(side,side+74),(29,42,36));page.paste(im,(0,74));dd=ImageDraw.Draw(page)
        dd.text((14,10),aid+' / unique UV atlas',font=font(22),fill=(230,233,219))
        dd.text((14,42),f'{a["charts"]} charts | {a["atlas_size"]}² | {a["effective_texel_density_px_m"]} effective px/m | 3 px gutters',font=font(14),fill=(174,193,175))
        page.save(ROOT/f'previews/UV_{aid}.png')
    Image.open(ROOT/'previews/scene_camera.png').convert('RGB').save(ROOT/'previews/scene_camera.jpg',quality=94,subsampling=0)
    print('Actual mesh contact sheet and UV examples saved.')

if __name__=='__main__':main()
