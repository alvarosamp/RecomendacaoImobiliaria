from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

out = Path('output/pdf/recomendacao_imobiliaria_relatorio_executivo.pdf')
out.parent.mkdir(parents=True, exist_ok=True)
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Lead', parent=styles['BodyText'], leading=16, spaceAfter=10))
doc = SimpleDocTemplate(str(out), pagesize=A4, rightMargin=1.7*cm, leftMargin=1.7*cm, topMargin=1.6*cm, bottomMargin=1.6*cm)
story = [Paragraph('Relatorio Executivo - Inteligencia Imobiliaria', styles['Title']), Spacer(1, 8),
         Paragraph('Pouso Alegre, MG | Base territorial consolidada em 24/08/2026', styles['Lead']),
         Paragraph('Este relatorio consolida dados publicos e analiticos para apoiar triagem imobiliaria. Nao substitui avaliacao, licenca, certidao ou laudo tecnico.', styles['BodyText']), Spacer(1, 12)]
rows = [['Camada', 'Cobertura / resultado'], ['Grade territorial', '711 celulas H3'], ['Censo IBGE 2022', '151.753 habitantes e 55.829 domicilios agregados'], ['Carta SGB/CPRM', '3.922 poligonos oficiais de suscetibilidade'], ['Hidrografia OSM', '1.565 elementos e distancia a drenagem'], ['MapBiomas', 'Cobertura 2019 e 2024 por celula'], ['Mercado local', 'Preco por m2 e comparaveis por bairro']]
t = Table(rows, colWidths=[5.1*cm, 10.2*cm])
t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#17324d')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#d8dee6')),('VALIGN',(0,0),(-1,-1),'TOP'),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('PADDING',(0,0),(-1,-1),7)]))
story += [Paragraph('Base de evidencias', styles['Heading2']), t, Spacer(1, 14), Paragraph('Como interpretar', styles['Heading2']), Paragraph('Priorize areas com score alto, uso do solo compativel e risco controlado. Qualquer indicio oficial de inundacao, deslizamento, agua, area alagada ou cobertura florestal deve ser validado antes de avancar.', styles['BodyText']), Spacer(1, 10), Paragraph('Fontes: IBGE Censo 2022; Servico Geologico do Brasil (SGB/CPRM); MapBiomas Colecao 10; OpenStreetMap; anuncios locais normalizados.', styles['BodyText'])]
doc.build(story)
