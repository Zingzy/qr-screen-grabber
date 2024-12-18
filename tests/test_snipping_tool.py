import pytest
from unittest.mock import MagicMock, patch, Mock
from PIL import Image
from src.ui.snipping_tool import TkinterSnippingTool


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for the TkinterSnippingTool"""
    return {
        "qr_processor": MagicMock(),
        "screenshot_service": MagicMock(),
        "clipboard_service": MagicMock(),
        "notification_service": MagicMock(),
        "icon_path": MagicMock(),
    }


@pytest.fixture
def snipping_tool(mock_dependencies):
    """Create a TkinterSnippingTool instance with mock dependencies"""
    return TkinterSnippingTool(
        qr_processor=mock_dependencies["qr_processor"],
        screenshot_service=mock_dependencies["screenshot_service"],
        clipboard_service=mock_dependencies["clipboard_service"],
        notification_service=mock_dependencies["notification_service"],
        icon_path=mock_dependencies["icon_path"],
    )


def test_initial_state(snipping_tool):
    """Test the initial state of the TkinterSnippingTool"""
    assert snipping_tool.snip_surface is None
    assert snipping_tool.master_screen is None
    assert snipping_tool.start_x is None
    assert snipping_tool.start_y is None
    assert not snipping_tool.is_window_displayed


def test_show_window(snipping_tool, mock_dependencies):
    """Test the show_window method"""
    # Create a mock Tk window
    snipping_tool.master_screen = MagicMock()
    snipping_tool.master_screen.winfo_exists.return_value = True

    # Create a mock Canvas widget
    snipping_tool.snip_surface = MagicMock()

    snipping_tool.show_window()

    # Verify that the window was deiconified and in the right state
    snipping_tool.snip_surface.delete.assert_called_once_with("all")
    assert snipping_tool.master_screen.update.call_count == 30  # alpha_cycles
    assert (
        snipping_tool.master_screen.wm_attributes.call_count == 31
    )  # alpha_cycles + 1
    snipping_tool.master_screen.deiconify.assert_called_once()
    assert snipping_tool.alpha == 0.3  # max_alpha
    assert snipping_tool.is_window_displayed


def test_hide_window(snipping_tool, mock_dependencies):
    """Test the hide_window method"""
    # Create a mock Tk window
    snipping_tool.master_screen = MagicMock()
    snipping_tool.master_screen.winfo_exists.return_value = True
    snipping_tool.is_window_displayed = True

    snipping_tool.hide_window()

    # Verify that the window was withdrawn and in the right state
    assert snipping_tool.master_screen.update.call_count == 30  # alpha_cycles
    assert snipping_tool.master_screen.wm_attributes.call_count == 30  # alpha_cycles
    snipping_tool.master_screen.withdraw.assert_called_once()
    assert snipping_tool.alpha == 0
    assert not snipping_tool.is_window_displayed


def test_hide_window_no_existing_window(snipping_tool):
    """Test hide_window when no window exists"""
    snipping_tool.master_screen = None

    try:
        snipping_tool.hide_window()
    except Exception as e:
        pytest.fail(f"hide_window raised an unexpected exception: {e}")


@pytest.mark.skipif(reason="Fails because physical window gets created")
@patch("tkinter.Canvas")
@patch("tkinter.Tk")
def test_initialize(mock_tk_class, mock_canvas_class, snipping_tool):
    # Setup mock Tk instance
    mock_tk = Mock()
    mock_tk_class.return_value = mock_tk
    mock_tk.winfo_screenwidth.return_value = 1920
    mock_tk.winfo_screenheight.return_value = 1080

    # Setup mock Canvas
    mock_canvas = Mock()
    mock_canvas_class.return_value = mock_canvas

    # Call the method
    snipping_tool.initialize()

    # Verify Tk window setup
    mock_tk.attributes.assert_any_call("-transparent", "blue")
    mock_tk.attributes.assert_any_call("-topmost", True)
    mock_tk.attributes.assert_any_call("-fullscreen", True)

    # Verify Canvas setup
    mock_canvas_class.assert_called_once_with(mock_tk, cursor="crosshair", bg="grey18")
    mock_canvas.pack.assert_called_once()

    # Verify event bindings
    mock_canvas.bind.assert_any_call("<ButtonPress-1>", snipping_tool.on_button_press)
    mock_canvas.bind.assert_any_call("<B1-Motion>", snipping_tool.on_snip_drag)
    mock_canvas.bind.assert_any_call(
        "<ButtonRelease-1>", snipping_tool.on_button_release
    )
    mock_canvas.bind.assert_any_call("<Escape>", snipping_tool.hide_window)


def test_on_button_press(snipping_tool):
    """Test on_button_press method"""
    # Create a mock canvas and event
    snipping_tool.snip_surface = MagicMock()
    snipping_tool.snip_surface.canvasx.return_value = 100
    snipping_tool.snip_surface.canvasy.return_value = 200

    event = MagicMock()
    event.x = 100
    event.y = 200

    snipping_tool.on_button_press(event)

    # Check if the cursor moved
    assert not snipping_tool.cursor_moved

    # Verify start coordinates and rectangle creation
    assert snipping_tool.start_x == 100
    assert snipping_tool.start_y == 200
    snipping_tool.snip_surface.create_rectangle.assert_called_once()


def test_on_snip_drag(snipping_tool):
    """Test on_snip_drag method"""
    # Create a mock canvas and rectangle
    snipping_tool.snip_surface = MagicMock()
    snipping_tool.rect = 1  # Mock rectangle ID
    snipping_tool.start_x = 50
    snipping_tool.start_y = 50

    event = MagicMock()
    event.x = 200
    event.y = 250

    snipping_tool.on_snip_drag(event)

    # Check if the cursor moved
    assert snipping_tool.cursor_moved

    # Verify rectangle coordinates updated
    snipping_tool.snip_surface.coords.assert_called_with(
        snipping_tool.rect, 50, 50, 200, 250
    )


def test_process_screenshot_with_qr_code(snipping_tool, mock_dependencies):
    """Test process_screenshot when a QR code is detected"""
    # Mock dependencies
    mock_qr_processor = mock_dependencies["qr_processor"]
    mock_clipboard_service = mock_dependencies["clipboard_service"]
    mock_notification_service = mock_dependencies["notification_service"]

    # Create a mock image
    mock_image = MagicMock(spec=Image.Image)

    # Simulate QR code detection
    mock_qr_processor.detect_qr_code.return_value = ("test_data", True)

    snipping_tool.process_screenshot(mock_image)

    # Verify interactions
    mock_qr_processor.detect_qr_code.assert_called_with(mock_image)
    mock_clipboard_service.copy_to_clipboard.assert_called_with("test_data")
    mock_notification_service.show_notification.assert_called_with(
        "QR Code Detected", "QR Code data copied to clipboard:\n\n" + "test_data"
    )


def test_process_screenshot_no_qr_code(snipping_tool, mock_dependencies):
    """Test process_screenshot when no QR code is detected"""
    # Mock dependencies
    mock_qr_processor = mock_dependencies["qr_processor"]
    mock_notification_service = mock_dependencies["notification_service"]

    # Create a mock image
    mock_image = MagicMock(spec=Image.Image)

    # Simulate no QR code detection
    mock_qr_processor.detect_qr_code.return_value = (None, False)

    snipping_tool.process_screenshot(mock_image)

    # Verify interactions
    mock_qr_processor.detect_qr_code.assert_called_with(mock_image)
    mock_notification_service.show_notification.assert_called_with(
        "No QR Code Detected", "No QR Code was detected in the screenshot."
    )


def test_long_qr_code_data_truncation(snipping_tool, mock_dependencies):
    """Test that long QR code data is truncated in notification"""
    # Mock dependencies
    mock_qr_processor = mock_dependencies["qr_processor"]
    mock_notification_service = mock_dependencies["notification_service"]

    # Create a mock image
    mock_image = MagicMock(spec=Image.Image)

    # Simulate long QR code data
    long_data = "x" * 300
    mock_qr_processor.detect_qr_code.return_value = (long_data, True)

    snipping_tool.process_screenshot(mock_image)

    # Verify data is truncated
    mock_notification_service.show_notification.assert_called_with(
        "QR Code Detected",
        "QR Code data copied to clipboard:\n\n" + f"{long_data[:200]}...",
    )
