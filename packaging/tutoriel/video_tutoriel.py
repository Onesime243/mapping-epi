"""Vidéo du tutoriel Mapping Épi avec voix off (voix française du Mac), à partir des captures du tutoriel cliquable.

Usage (depuis la racine du projet, sur Mac) :
    .venv/bin/python packaging/tutoriel/video_tutoriel.py "/chemin/Tutoriel_video_Mapping_Epi.mp4" [voix]

Chaque étape : la capture réelle de l'outil, la zone à cliquer encadrée en rouge, le titre et la valeur saisie en bas,
et la voix off qui explique. Encodage MP4 (H.264 + AAC) par Qt Multimedia, sans autre logiciel. Un fichier de
sous-titres .srt est écrit à côté de la vidéo.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TUTO = ROOT / "web" / "static" / "tutoriel"
W, H, FPS = 1920, 1080, 5
VOIX = sys.argv[2] if len(sys.argv) > 2 else "Thomas"
SR = 24000

# ------------------------------------------------------------------------------------------------ texte de la voix off
INTRO = ("Bienvenue dans ce tutoriel Mapping Épi. En une dizaine de minutes, vous allez voir comment remplir la fiche "
         "d'un cas confirmé de maladie à virus Ebola, étape par étape, pour produire son mapping : le parcours "
         "thérapeutique du cas. Nous utilisons un cas fictif d'exercice. Aucune donnée réelle n'est montrée.")
CHAPITRES = {
    "web": ("Partie 1 : la saisie dans l'outil", "Commençons par la saisie complète d'un cas, directement dans l'outil, "
            "de la connexion jusqu'au mapping final."),
    "fiche": ("Partie 2 : corriger avec Word ou Excel", "Deuxième partie : comment télécharger la fiche remplie, la "
              "corriger dans Word ou dans Excel, puis la réimporter dans le même mapping."),
    "narr": ("Partie 3 : importer un narratif", "Troisième partie : vous avez déjà un narratif ou un rapport "
             "d'investigation au format Word ? L'outil peut le lire et pré-remplir la fiche."),
}
OUTRO = ("Voilà. Vous savez maintenant remplir une fiche Mapping Épi étape par étape, la corriger avec Word ou Excel, "
         "et importer un narratif. Pensez à toujours compléter les cases rouges, à n'écrire que des identifiants, "
         "jamais de noms de personnes, et à mettre la fiche à jour dès qu'une nouvelle information arrive. Merci.")

NARRATION = {
    "t01": "Ouvrez l'adresse de Mapping Épi dans votre navigateur. Dans le champ Identifiant, tapez l'identifiant que "
           "l'administrateur vous a donné. Ici : z s point bikoro.",
    "t02": "Tapez ensuite votre mot de passe personnel. Ne le partagez avec personne.",
    "t03": "Cliquez sur Se connecter.",
    "t04": "La page d'accueil s'ouvre. Elle propose de créer un nouveau cas, ou d'importer une fiche déjà remplie en Word "
           "ou en Excel. Pour une saisie directe, cliquez sur Nouveau cas.",
    "t05": "La fiche s'ouvre. Elle se remplit par étapes : la liste à gauche montre les huit étapes, de l'identité aux "
           "actions. Une coche verte signale une étape complète ; l'orange signale ce qui manque. L'aperçu du mapping "
           "se trouve à droite, et il se met à jour à chaque saisie.",
    "t06": "Étape 1, l'identité. Tapez l'identifiant du cas, c'est-à-dire son numéro EPID, en lettres et en chiffres. "
           "Par exemple : démo, B I K, 26, 003. La fiche s'enregistre toute seule : vous voyez le message Enregistré en haut.",
    "t07": "Le cas était-il déjà un contact listé ? Cliquez sur le bon bouton : Inconnu, Contact connu, Contact connu suivi, "
           "ou Non contact. Ici, c'est un contact connu.",
    "t08": "Pour un contact connu, deux champs deviennent obligatoires : l'identifiant du cas source, et la date du dernier "
           "contact avec lui. Tant qu'ils sont vides, les cases restent rouges.",
    "t09": "Choisissez le sexe, tapez l'âge et la profession. Si l'âge est inconnu, laissez la case vide : le mapping "
           "affichera un point d'interrogation, jamais un zéro.",
    "t10": "Indiquez si le cas est un agent de santé, et s'il était vacciné. La date de début de la vaccination en anneau "
           "se renseigne dès qu'elle est connue.",
    "t11": "Choisissez la province, puis la zone de santé, puis l'aire de santé. Chaque liste se filtre selon la précédente. "
           "Ici : Équateur, zone de santé de Bikoro, aire de santé de Penzele.",
    "t12": "Complétez la date de notification, la date de confirmation, l'état du cas, et l'équipe d'investigation.",
    "t13": "L'étape Identité est maintenant cochée en vert. Passez à l'étape 2 : Clinique.",
    "t14": "Tapez la date de début des symptômes rapportée par l'équipe, et la phase des premiers signes. L'outil en déduit "
           "le jour zéro retenu, la période d'exposition probable, et les phases de la maladie.",
    "t15": "Cochez les symptômes rapportés. Ils sont rangés comme sur le schéma des phases : phase sèche, phase humide, "
           "puis signes hémorragiques.",
    "t16": "Passez à l'étape 3 : la chronologie. C'est le cœur du mapping : une ligne par étape du parcours du cas, de "
           "l'exposition jusqu'à la riposte.",
    "t17": "Cliquez sur Ajouter une étape, puis remplissez la ligne : la date de début, et la date de fin pour une période, "
           "le lieu, le type d'étape, un titre court, une description, et les personnes présentes. Laissez le risque vide : "
           "l'outil le calcule. Première étape : l'exposition probable au marché de Penzele, du 2 au 15 juillet.",
    "t18": "Deuxième étape : le début de la maladie, le 19 juillet, au centre de santé de Penzele, avec fièvre, fatigue et "
           "céphalées. Regardez l'aperçu à droite : une nouvelle carte apparaît.",
    "t19": "Troisième étape : la référence vers l'hôpital général de Bikoro, le 24 juillet, à moto. Pour un déplacement, "
           "remplissez aussi le lieu d'arrivée et le moyen de transport.",
    "t20": "Quatrième étape : l'hospitalisation, du 24 au 27 juillet, avec vomissements, diarrhée et saignements des gencives. "
           "Cochez Liquides biologiques : le risque augmente d'un niveau.",
    "t21": "Cinquième étape : le décès à l'hôpital, puis le retour du corps au village en véhicule privé. Cochez Contact corps.",
    "t22": "Sixième étape : les funérailles et l'enterrement, sans sécurisation du corps. Le risque devient très élevé.",
    "t23": "Septième étape : le résultat positif du laboratoire. Pour une étape sans personnes exposées, comme le laboratoire, "
           "le champ Personnes présentes n'est pas exigé. Le mapping montre maintenant tout le parcours.",
    "t24": "Le bouton Trier par date remet les étapes dans l'ordre. La liste à gauche indique que la chronologie est complète.",
    "t25": "Étape 4 : les lieux. Cliquez sur Pré-remplir depuis la chronologie : tous les lieux des étapes sont ajoutés. "
           "Complétez ensuite les personnes exposées et leur nombre.",
    "t26": "Étape 5 : les contacts. Ajoutez une ligne par catégorie : le nombre de contacts, le nombre suivis, le risque, "
           "le lieu, la date du dernier contact, et le nombre de vaccinés. Si un nombre est inconnu, laissez la case vide.",
    "t27": "Étape 6 : la P C I. Pour chaque site, indiquez le statut de décontamination, la date, l'équipe, et l'adresse : "
           "avenue, quartier ou repère. L'adresse figure sur la carte du parcours et dans le menu P C I.",
    "t28": "Étape 7 : le laboratoire. Indiquez le type d'échantillon, le laboratoire, la date et l'heure du prélèvement et du "
           "résultat. Le délai est calculé automatiquement.",
    "t29": "Étape 8 : les actions. L'outil propose des actions en bas de page : cliquez sur Ajouter, ou décrivez la vôtre, avec "
           "sa priorité, le responsable, l'échéance, le pilier, et le statut. Passez-la à Fait quand elle est réalisée.",
    "t30": "L'onglet Contrôles liste les alertes à vérifier avant de diffuser le mapping : dates incohérentes, champs manquants, "
           "ou noms de personnes à retirer des textes.",
    "t31": "Pour bien lire le mapping, cliquez sur Plein écran : le visuel occupe tout l'écran, sans aucun téléchargement.",
    "t32": "En plein écran, les onglets permettent de passer au réseau de contacts ou à la carte du parcours. Cliquez sur "
           "Réduire, ou appuyez sur la touche Échap, pour revenir à la fiche.",
    "t33": "Pour partager le mapping, choisissez un format : P N G haute définition pour l'envoyer, P D F pour l'imprimer, "
           "PowerPoint pour une présentation modifiable.",
    "t_fin": "Et voici le résultat : le mapping complet du cas, avec son identité, la chronologie par phase de la maladie, "
             "les contacts, la P C I et les actions. Complétez la fiche dès qu'une nouvelle information arrive : le mapping "
             "se met à jour tout seul.",
    "r01": "Sous l'aperçu, les boutons Fiche Word et Fiche Excel téléchargent la fiche remplie avec tout ce qui est saisi. "
           "Vous pouvez la corriger tranquillement, même sans connexion.",
    "r_fin": "Une fois corrigée, choisissez le fichier, puis cliquez sur Réimporter dans cette fiche. Le même mapping est mis "
             "à jour, sans créer de doublon. L'état précédent reste dans l'historique des versions.",
    "n01": "Sur la page Importer une fiche, choisissez votre narratif ou votre rapport d'investigation au format Word. Le "
           "modèle de terrain, en point doc ou point docx, est reconnu.",
    "n02": "Cliquez sur Importer et ouvrir la fiche. L'outil lit le document et remplit la fiche : identité, dates, chronologie, "
           "symptômes, contacts et actions.",
    "n03": "Le message liste ce qui a été trouvé et ce qui reste à compléter. Rien n'est inventé : une information absente "
           "du narratif reste vide, et les noms de personnes ne sont jamais repris.",
    "n04": "Ouvrez la chronologie : chaque phrase datée du récit est devenue une étape. Vérifiez chaque ligne et complétez "
           "les cases rouges, comme les personnes présentes.",
    "n_fin": "Le mapping est produit directement à partir du narratif. Les informations manquantes apparaissent à compléter, "
             "en rouge, jusqu'à ce que la fiche soit complète.",
}


# ------------------------------------------------------------------------------------------------ voix
def voix(texte: str, dossier: Path, nom: str) -> bytes:
    f = dossier / f"{nom}.wav"
    subprocess.run(["say", "-v", VOIX, "-r", "168", "-o", str(f), f"--data-format=LEI16@{SR}", texte], check=True)
    with wave.open(str(f)) as w:
        return w.readframes(w.getnframes())


def silence(sec: float) -> bytes:
    return b"\x00\x00" * int(SR * sec)


# ------------------------------------------------------------------------------------------------ images
def image_etape(img_path: Path, boite, titre: str, valeur: str, chapitre: str, num: str):
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen
    fond = QImage(str(img_path)).scaled(W, H, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    img = QImage(W, H, QImage.Format.Format_ARGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.drawImage(0, 0, fond)
    if boite:
        x, y, w, h = [v / 100 for v in boite]
        r = QRectF(x * W, y * H, w * W, h * H)
        voile = QPainterPath()
        voile.addRect(QRectF(0, 0, W, H))
        trou = QPainterPath()
        trou.addRoundedRect(r, 10, 10)
        p.fillPath(voile.subtracted(trou), QColor(10, 16, 26, 95))
        p.setPen(QPen(QColor("#E11D2E"), 6))
        p.drawRoundedRect(r, 10, 10)
    # bandeau du haut : partie et numéro d'étape
    p.fillRect(QRectF(0, 0, W, 54), QColor(31, 58, 95, 235))
    f = QFont("Helvetica Neue", 20)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor("white"))
    p.drawText(QRectF(28, 0, W - 56, 54), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, f"MAPPING ÉPI · {chapitre}")
    p.drawText(QRectF(28, 0, W - 56, 54), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, num)
    # bandeau du bas : titre de l'étape et valeur saisie
    hb = 118 if valeur else 86
    p.fillRect(QRectF(0, H - hb, W, hb), QColor(20, 27, 38, 232))
    f = QFont("Helvetica Neue", 30)
    f.setBold(True)
    p.setFont(f)
    p.drawText(QRectF(36, H - hb + 10, W - 72, 52), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, titre)
    if valeur:
        f = QFont("Menlo", 21)
        p.setFont(f)
        p.setPen(QColor("#FFD27A"))
        p.drawText(QRectF(36, H - hb + 60, W - 72, 44), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   "À saisir : " + valeur)
    p.end()
    return img


def image_titre(titre: str, sous: str):
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter
    img = QImage(W, H, QImage.Format.Format_ARGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    g = QLinearGradient(0, 0, W, H)
    g.setColorAt(0, QColor("#1F3A5F"))
    g.setColorAt(1, QColor("#13243A"))
    p.fillRect(QRectF(0, 0, W, H), g)
    for i, c in enumerate(("#1D5FAF", "#C8202A", "#F2B705")):
        p.fillRect(QRectF(i * W / 3, H - 14, W / 3, 14), QColor(c))
    sceau = ROOT / "web" / "static" / "sceau_presidence.png"
    if sceau.exists():
        s = __import__("PySide6.QtGui", fromlist=["QImage"]).QImage(str(sceau))
        p.drawImage(QRectF(W / 2 - 80, 150, 160, 160), s)
    f = QFont("Helvetica Neue", 22)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor("#9CC2EA"))
    p.drawText(QRectF(0, 340, W, 50), Qt.AlignmentFlag.AlignCenter, "TASK FORCE PRÉSIDENTIELLE EBOLA 17 · MAPPING ÉPI")
    f = QFont("Helvetica Neue", 54)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor("white"))
    p.drawText(QRectF(80, 420, W - 160, 200), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, titre)
    f = QFont("Helvetica Neue", 28)
    p.setFont(f)
    p.setPen(QColor("#DCE6F2"))
    p.drawText(QRectF(160, 640, W - 320, 220), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, sous)
    p.end()
    return img


# ------------------------------------------------------------------------------------------------ montage
def scenes(tmp: Path):
    s = (TUTO / "index.html").read_text(encoding="utf-8")
    data = json.loads(re.search(r"const DATA = (\{.*?\});\n", s, re.S).group(1))
    out = [(image_titre("Remplir une fiche Mapping Épi, étape par étape", "Tutoriel vidéo · cas fictif d'exercice · aucune donnée réelle"),
            voix(INTRO, tmp, "intro"), INTRO)]
    for ch in ("web", "fiche", "narr"):
        t, txt = CHAPITRES[ch]
        out.append((image_titre(t, ""), voix(txt, tmp, f"ch_{ch}"), txt))
        etapes = data[ch]
        for k, e in enumerate(etapes, 1):
            cle = Path(e["img"]).stem
            parle = NARRATION.get(cle, e["title"] + ". " + e["text"])
            img = image_etape(TUTO / e["img"], e.get("box"), e["title"], e.get("value") or "", t.split(" : ")[-1],
                              f"étape {k} / {len(etapes)}")
            out.append((img, voix(parle, tmp, cle), parle))
            print(f"{cle:6} {e['title']}", flush=True)
    out.append((image_titre("Merci", "Mapping Épi · Système de Gestion de l'Incident MVE 17\nSGI-RDC avec l'appui de UMIE-INRB"),
                voix(OUTRO, tmp, "outro"), OUTRO))
    return out


def encoder(liste, sortie: Path):
    from PySide6.QtCore import QSize, QTimer, QUrl
    from PySide6.QtGui import QImage
    from PySide6.QtMultimedia import (QAudioBuffer, QAudioBufferInput, QAudioFormat, QMediaCaptureSession, QMediaFormat,
                                      QMediaRecorder, QVideoFrame, QVideoFrameFormat, QVideoFrameInput)
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    # piste son complète et liste des images à chaque instant (0,6 s de pause entre les étapes)
    pcm, plan = b"", []
    for img, son, _t in liste:
        bloc = silence(0.5) + son + silence(0.7)
        plan.append((img.convertToFormat(QImage.Format.Format_ARGB32), len(bloc) / 2 / SR))
        pcm += bloc
    n_images = []
    for img, d in plan:
        n_images.append((img, max(1, round(d * FPS))))
    total = sum(n for _i, n in n_images)
    pcm = pcm[: total * SR // FPS * 2].ljust(total * SR // FPS * 2, b"\x00")
    session = QMediaCaptureSession()
    vin = QVideoFrameInput(QVideoFrameFormat(QSize(W, H), QVideoFrameFormat.PixelFormat.Format_BGRA8888))
    fmt = QAudioFormat()
    fmt.setSampleRate(SR)
    fmt.setChannelCount(1)
    fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
    ain = QAudioBufferInput(fmt)
    session.setVideoFrameInput(vin)
    session.setAudioBufferInput(ain)
    rec = QMediaRecorder()
    session.setRecorder(rec)
    mf = QMediaFormat(QMediaFormat.FileFormat.MPEG4)
    mf.setVideoCodec(QMediaFormat.VideoCodec.H264)
    mf.setAudioCodec(QMediaFormat.AudioCodec.AAC)
    rec.setMediaFormat(mf)
    rec.setQuality(QMediaRecorder.Quality.HighQuality)
    rec.setVideoFrameRate(FPS)
    rec.setVideoResolution(W, H)
    rec.setOutputLocation(QUrl.fromLocalFile(str(sortie)))
    rec.errorOccurred.connect(lambda e, s: print("Erreur d'encodage :", e, s))
    images = [img for img, n in n_images for _ in range(n)]
    etat = {"v": 0, "a": 0, "fin_v": False, "fin_a": False}
    morceau = SR // FPS * 2

    def terminer():
        # les deux pistes sont envoyées : on ferme le fichier (sinon le MP4 n'est pas finalisé)
        if etat["fin_v"] and etat["fin_a"]:
            print("  fermeture du fichier…", flush=True)
            QTimer.singleShot(500, rec.stop)

    def video():
        if etat["v"] >= len(images):
            etat["fin_v"] = True
            terminer()
            return
        fr = QVideoFrame(images[etat["v"]])
        fr.setStartTime(int(etat["v"] * 1e6 / FPS))
        fr.setEndTime(int((etat["v"] + 1) * 1e6 / FPS))
        if vin.sendVideoFrame(fr):
            etat["v"] += 1
            if etat["v"] % 500 == 0:
                print(f"  images {etat['v']} / {len(images)}", flush=True)
        QTimer.singleShot(0, video)

    def audio():
        if etat["a"] >= len(pcm):
            etat["fin_a"] = True
            terminer()
            return
        ch = pcm[etat["a"]:etat["a"] + morceau]
        if ain.sendAudioBuffer(QAudioBuffer(ch, fmt, int(etat["a"] / 2 * 1e6 / SR))):
            etat["a"] += len(ch)
        QTimer.singleShot(0, audio)

    rec.recorderStateChanged.connect(lambda st: app.quit() if st == QMediaRecorder.RecorderState.StoppedState else None)
    rec.record()
    QTimer.singleShot(300, video)
    QTimer.singleShot(300, audio)
    app.exec()
    return total / FPS


def srt(liste, sortie: Path):
    def h(t):
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    t, lignes = 0.0, []
    for k, (_img, son, texte) in enumerate(liste, 1):
        d = len(silence(0.5) + son + silence(0.7)) / 2 / SR
        lignes += [str(k), f"{h(t + 0.5)} --> {h(t + d - 0.7)}", texte, ""]
        t += d
    sortie.write_text("\n".join(lignes), encoding="utf-8")


if __name__ == "__main__":
    sortie = Path(sys.argv[1])
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv[:1])
    with tempfile.TemporaryDirectory() as d:
        liste = scenes(Path(d))
        duree = encoder(liste, sortie)
        srt(liste, sortie.with_suffix(".srt"))
    print(f"Vidéo : {sortie} · {duree / 60:.1f} min · {len(liste)} scènes")
