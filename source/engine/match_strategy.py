import cv2
import numpy as np

from typing import Protocol, List, Tuple


class MatchStrategy(Protocol):
    def find_matches(self, screen_image: np.ndarray, template_image: np.ndarray, conf: float) -> List[Tuple[int,int,int,int,float]]:
        """Returns a list of (x, y, w, h) bounding boxes."""
        ...


def _compute_normalized_map(result: np.ndarray, method: int) -> np.ndarray:
    """Return a 0..1 map of "confidence" for each location in result."""
    if method == cv2.TM_CCORR_NORMED:
        return result.astype(np.float32)
    if method == cv2.TM_CCOEFF_NORMED:
        return ((result.astype(np.float32) + 1.0) / 2.0)
    if method == cv2.TM_SQDIFF_NORMED:
        return 1.0 - result.astype(np.float32)

    return result.astype(np.float32)

def _find_local_peaks(norm_map: np.ndarray, min_distance: int, thresh: float) -> List[Tuple[int,int,float]]:
    """Return list of (x, y, score) local peaks where norm_map >= thresh."""
    if norm_map.size == 0:
        return []

    thresh = float(max(0.0, min(1.0, thresh)))

    k = max(1, int(min_distance))
    kernel = np.ones((k, k), dtype=np.uint8)

    dilated = cv2.dilate(norm_map, kernel)
    local_max = (norm_map == dilated)
    mask = (norm_map >= thresh) & local_max

    ys, xs = np.where(mask)
    peaks = []
    for y, x in zip(ys, xs):
        peaks.append((int(x), int(y), float(norm_map[y, x])))
    return peaks

def _nms_iou(boxes: List[Tuple[int,int,int,int,float]], iou_thresh: float = 0.3) -> List[Tuple[int,int,int,int,float]]:
    """NMS on boxes (x,y,w,h,score). Returns kept boxes sorted in descending score order."""
    if not boxes:
        return []
    arr = np.array(boxes, dtype=float)
    x1 = arr[:,0]
    y1 = arr[:,1]
    x2 = x1 + arr[:,2]
    y2 = y1 + arr[:,3]
    scores = arr[:,4]

    idxs = np.argsort(scores)[::-1]
    keep = []
    while idxs.size:
        i = idxs[0]
        keep.append((int(x1[i]), int(y1[i]), int(arr[i,2]), int(arr[i,3]), float(scores[i])))
        if idxs.size == 1:
            break
        xx1 = np.maximum(x1[i], x1[idxs[1:]])
        yy1 = np.maximum(y1[i], y1[idxs[1:]])
        xx2 = np.minimum(x2[i], x2[idxs[1:]])
        yy2 = np.minimum(y2[i], y2[idxs[1:]])

        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h
        area_i = (x2[i] - x1[i]) * (y2[i] - y1[i])
        area_others = (x2[idxs[1:]] - x1[idxs[1:]]) * (y2[idxs[1:]] - y1[idxs[1:]])
        union = area_i + area_others - inter
        iou = inter / (union + 1e-9)

        idxs = idxs[1:][iou <= iou_thresh]
    return keep


class TemplateGrayStrategy:
    def __init__(self, method: int = cv2.TM_CCOEFF_NORMED,
                 iou_threshold: float = 0.3, max_results: int = 10):
        self.method = method
        self.iou_threshold = float(iou_threshold)
        self.max_results = int(max_results)

    def _prepare(self, screen_image, template_image):
        if screen_image.ndim > 2:
            screen = cv2.cvtColor(screen_image, cv2.COLOR_BGR2GRAY)
        else:
            screen = screen_image
        if template_image.ndim > 2:
            tpl = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY)
        else:
            tpl = template_image

        if screen.dtype != np.uint8 and screen.dtype != np.float32:
            screen = screen.astype(np.uint8)
        if tpl.dtype != np.uint8 and tpl.dtype != np.float32:
            tpl = tpl.astype(np.uint8)

        return screen, tpl

    def find_matches(self, screen_image: np.ndarray, template_image: np.ndarray, conf: float) -> List[Tuple[int,int,int,int,float]]:
        screen, tpl = self._prepare(screen_image, template_image)

        th_tpl, tw_tpl = tpl.shape[:2]
        ih, iw = screen.shape[:2]
        if th_tpl > ih or tw_tpl > iw:
            return []

        res = cv2.matchTemplate(screen, tpl, self.method)
        norm = _compute_normalized_map(res, self.method).astype(np.float32)
        min_distance = max(3, min(tw_tpl, th_tpl) // 4)

        peaks = _find_local_peaks(norm, min_distance=min_distance, thresh=conf)
        if not peaks:
            return []

        w, h = tw_tpl, th_tpl
        boxes = [(x, y, w, h, score) for x, y, score in peaks]

        if len(boxes) > 200:
            boxes = sorted(boxes, key=lambda b: b[4], reverse=True)[:200]

        kept = _nms_iou(boxes, iou_thresh=self.iou_threshold)
        return sorted(kept, key=lambda b: b[4], reverse=True)[:self.max_results]


class TemplateRGBStrategy:
    """Template matching attempting multi-channel matching when possible.
       Falls back to grayscale when template or screen are single-channel.
    """
    def __init__(self, method: int = cv2.TM_CCOEFF_NORMED,
                 iou_threshold: float = 0.3, max_results: int = 10):
        self.method = method
        self.iou_threshold = float(iou_threshold)
        self.max_results = int(max_results)

    def _prepare(self, screen_image, template_image):
        # if both are 3-ch, leave as-is; otherwise convert both to gray
        if screen_image.ndim == 3 and template_image.ndim == 3 and screen_image.shape[2] == template_image.shape[2]:
            return screen_image, template_image
        # fallback to grayscale
        if screen_image.ndim > 2:
            screen = cv2.cvtColor(screen_image, cv2.COLOR_BGR2GRAY)
        else:
            screen = screen_image
        if template_image.ndim > 2:
            tpl = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY)
        else:
            tpl = template_image

        if screen.dtype != np.uint8 and screen.dtype != np.float32:
            screen = screen.astype(np.uint8)
        if tpl.dtype != np.uint8 and tpl.dtype != np.float32:
            tpl = tpl.astype(np.uint8)
        
        return screen, tpl

    def find_matches(self, screen_image: np.ndarray, template_image: np.ndarray, conf: float) -> List[Tuple[int,int,int,int,float]]:
        screen, tpl = self._prepare(screen_image, template_image)

        th_tpl, tw_tpl = tpl.shape[:2]
        ih, iw = screen.shape[:2]
        if th_tpl > ih or tw_tpl > iw:
            return []
        
        res = cv2.matchTemplate(screen, tpl, self.method)
        norm = _compute_normalized_map(res, self.method).astype(np.float32)
        min_distance = max(3, min(tw_tpl, th_tpl) // 4)

        peaks = _find_local_peaks(norm, min_distance=min_distance, thresh=conf)
        if not peaks:
            return []

        w, h = tw_tpl, th_tpl
        boxes = [(x, y, w, h, score) for x, y, score in peaks]

        if len(boxes) > 200:
            boxes = sorted(boxes, key=lambda b: b[4], reverse=True)[:200]

        kept = _nms_iou(boxes, iou_thresh=self.iou_threshold)
        return sorted(kept, key=lambda b: b[4], reverse=True)[:self.max_results]


class TemplateEdgesStrategy(TemplateGrayStrategy):
    """Edge-based matching: Canny both images then template-match."""
    def __init__(self, method: int = cv2.TM_CCOEFF_NORMED, th1: int = 100, th2: int = 200,
                 iou_threshold: float = 0.3, max_results: int = 10):
        self.method = method
        self.th1 = int(th1)
        self.th2 = int(th2)
        self.iou_threshold = float(iou_threshold)
        self.max_results = int(max_results)

    def _to_edges(self, screen_image, template_image):
        if screen_image.ndim > 2:
            screen_gray = cv2.cvtColor(screen_image, cv2.COLOR_BGR2GRAY)
        else:
            screen_gray = screen_image
        if template_image.ndim > 2:
            tpl_gray = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY)
        else:
            tpl_gray = template_image
        screen_edges = cv2.Canny(screen_gray, self.th1, self.th2)
        tpl_edges = cv2.Canny(tpl_gray, self.th1, self.th2)
        return screen_edges, tpl_edges

    def find_matches(self, screen_image: np.ndarray, template_image: np.ndarray, conf: float) -> List[Tuple[int,int,int,int,float]]:
        screen_edges, tpl_edges = self._to_edges(screen_image, template_image)

        th_tpl, tw_tpl = tpl_edges.shape[:2]
        ih, iw = screen_edges.shape[:2]
        if th_tpl > ih or tw_tpl > iw:
            return []

        res = cv2.matchTemplate(screen_edges, tpl_edges, self.method)
        norm = _compute_normalized_map(res, self.method).astype(np.float32)

        min_distance = max(3, min(tw_tpl, th_tpl) // 5)
        peaks = _find_local_peaks(norm, min_distance=min_distance, thresh=conf)
        if not peaks:
            return []

        w, h = tw_tpl, th_tpl
        boxes = [(x, y, w, h, score) for x, y, score in peaks]
        if len(boxes) > 200:
            boxes = sorted(boxes, key=lambda b: b[4], reverse=True)[:200]

        kept = _nms_iou(boxes, iou_thresh=self.iou_threshold)
        kept_sorted = sorted(kept, key=lambda b: b[4], reverse=True)[:self.max_results]
        return kept_sorted


class SIFTMatchStrategy:
    def __init__(self, min_matches: int = 40, inlier_ratio: float = 0.25):
        self.min_matches = int(min_matches)
        self.inlier_ratio = float(inlier_ratio)
        self.sift = cv2.SIFT_create(nfeatures=2000, contrastThreshold=0)

        # Cache storage for the screen
        self._last_screen_id = None
        self._last_kp2 = None
        self._last_des2 = None

    def find_matches(self, screen_image: np.ndarray, template_image: np.ndarray, conf: float = 0.0) -> List[Tuple[int,int,int,int,float]]:
        tpl_gray = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY) if template_image.ndim > 2 else template_image
        kp1, des1 = self.sift.detectAndCompute(tpl_gray, None)
        
        if des1 is None or len(kp1) < 2:
            return []

        current_screen_id = id(screen_image)
        if current_screen_id != self._last_screen_id:
            screen_gray = cv2.cvtColor(screen_image, cv2.COLOR_BGR2GRAY) if screen_image.ndim > 2 else screen_image
            self._last_kp2, self._last_des2 = self.sift.detectAndCompute(screen_gray, None)
            self._last_screen_id = current_screen_id

        kp2, des2 = self._last_kp2, self._last_des2
        
        if des2 is None or len(kp2) < 2:
            return []

        bf = cv2.BFMatcher(cv2.NORM_L2)
        good = bf.match(des1, des2)

        if len(good) < self.min_matches:
            return []

        src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1,1,2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1,1,2)

        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, maxIters=200)
        if M is None or mask is None:
            return []

        mask = mask.ravel()
        inliers = int(mask.sum())
        if inliers < self.inlier_ratio * len(good):
            return []

        # compute bounding polygon -> bbox
        h_tpl, w_tpl = tpl_gray.shape[:2]
        pts = np.float32([[0,0],[w_tpl,0],[w_tpl,h_tpl],[0,h_tpl]]).reshape(-1,1,2)
        dst = cv2.perspectiveTransform(pts, M)
        xs = dst[:,0,0]; ys = dst[:,0,1]
        x_min = int(np.min(xs)); y_min = int(np.min(ys))
        x_max = int(np.max(xs)); y_max = int(np.max(ys))
        width = max(1, x_max - x_min); height = max(1, y_max - y_min)

        score = float(inliers) / float(max(1, len(good)))
        return [(x_min, y_min, width, height, score)]
